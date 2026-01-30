import os
import logging
import operator
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.schema import CompanyInfo, Contact, Metrics
from src.tools import (
    TavilySearchWrapper, 
    scrape_with_bs4, 
    scrape_ufficiocamerale, 
    scrape_arera, 
    scrape_website_contacts
)
from src.llm_factory import get_llm

logger = logging.getLogger("atmio.agents")


def merge_company_info(old: Optional[CompanyInfo], new: Optional[CompanyInfo]) -> CompanyInfo:
    if not old:
        return new or CompanyInfo(name="Unknown")
    if not new:
        return old
    
    data = old.dict()
    new_data = new.dict(exclude_unset=True)
    
    if 'contacts' in new_data:
        existing_names = {c.get('name') for c in data.get('contacts', [])}
        for contact in new_data['contacts']:
            if contact.get('name') not in existing_names:
                data.setdefault('contacts', []).append(contact)
        del new_data['contacts']
        
    if 'metrics' in new_data and new_data['metrics']:
        data['metrics'] = new_data['metrics']
        del new_data['metrics']
        
    data.update(new_data)
    return CompanyInfo(**data)


class AgentState(TypedDict):
    company_name: str
    company_info: Annotated[CompanyInfo, merge_company_info]
    messages: Annotated[List[BaseMessage], operator.add]


class BaseAgent:
    def __init__(self):
        self.llm = get_llm()
        self.tavily = TavilySearchWrapper()

    def search(self, query: str) -> str:
        results = self.tavily.search(query)
        return "\n".join([f"- {r.get('title', 'No Title')}: {r.get('content', 'No Content')} ({r.get('url')})" for r in results])


class LegalAgent(BaseAgent):
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        company_name = state["company_name"]
        logger.info(f"LegalAgent starting for {company_name}")
        
        query = f"{company_name} official website company description industry headquarters"
        search_context = self.search(query)
        
        ufficio_context = scrape_ufficiocamerale(company_name) or ""
        if ufficio_context:
            search_context += f"\n\nUfficioCamerale Data:\n{ufficio_context[:2000]}"
            
        arera_context = scrape_arera(company_name) or ""
        if arera_context:
            search_context += f"\n\nArera Data:\n{arera_context[:2000]}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a corporate research agent. Extract the official company name, description, industry, and website from the search results."),
            ("user", "Company: {company}\n\nSearch Results:\n{context}\n\nExtract CompanyInfo (ignore contacts/metrics for now).")
        ])
        
        runnable = prompt | self.llm.with_structured_output(CompanyInfo)
        
        try:
            result = runnable.invoke({"company": company_name, "context": search_context})
            logger.info(f"LegalAgent found: {result.name}")
            return {"company_info": result}
        except Exception as e:
            logger.error(f"LegalAgent failed: {e}")
            return {"messages": [SystemMessage(content=f"LegalAgent Error: {str(e)}")]}


class ContactAgent(BaseAgent):
    
    class ContactsResult(BaseModel):
        contacts: List[Contact]

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        company_info = state.get("company_info")
        name = company_info.name if company_info else state["company_name"]
        website = company_info.website if company_info else None
        
        logger.info(f"ContactAgent starting for {name}")
        
        search_context = ""
        
        # 1. Scrape Website if available
        if website:
            logger.info(f"Scraping website for contacts: {website}")
            website_content = scrape_website_contacts(website)
            if website_content:
                search_context += f"\n\nWebsite Content:\n{website_content[:5000]}"
        
        # 2. General Search
        query = f"{name} key executives leadership team CEO CTO contacts email"
        search_context += "\n\nSearch Results:\n" + self.search(query)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a recruitment research agent. Extract a list of key contacts (Name, Role, Email) from the provided text.
            Prioritize contacts found on the company website.
            Valid emails are crucial. Generic emails (info@, sales@) are acceptable ONLY if no personal emails are found."""),
            ("user", "Company: {company}\n\nContext:\n{context}\n\nExtract contacts.")
        ])
        
        runnable = prompt | self.llm.with_structured_output(self.ContactsResult)
        
        try:
            result = runnable.invoke({"company": name, "context": search_context})
            logger.info(f"ContactAgent found {len(result.contacts)} contacts")
            return {"company_info": CompanyInfo(name=name, contacts=result.contacts)}
        except Exception as e:
            logger.error(f"ContactAgent failed: {e}")
            return {"messages": [SystemMessage(content=f"ContactAgent Error: {str(e)}")]}


class MetricsAgent(BaseAgent):
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        company_info = state.get("company_info")
        name = company_info.name if company_info else state["company_name"]
        logger.info(f"MetricsAgent starting for {name}")
        
        query = f"{name} annual revenue number of employees growth rate financial metrics"
        search_context = self.search(query)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a financial analyst. Extract revenue, employee count, and growth rate."),
            ("user", "Company: {company}\n\nSearch Results:\n{context}\n\nExtract Metrics.")
        ])
        
        runnable = prompt | self.llm.with_structured_output(Metrics)
        
        try:
            result = runnable.invoke({"company": name, "context": search_context})
            logger.info(f"MetricsAgent found info")
            return {"company_info": CompanyInfo(name=name, metrics=result)}
        except Exception as e:
            logger.error(f"MetricsAgent failed: {e}")
            return {"messages": [SystemMessage(content=f"MetricsAgent Error: {str(e)}")]}


class SafetyAgent(BaseAgent):
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        logger.info("SafetyAgent validating data")
        info = state.get("company_info")
        
        messages = []
        if not info:
            messages.append(SystemMessage(content="Safety Alert: No company info extracted."))
            return {"messages": messages}
            
        if info.name == "Unknown" or not info.name:
             messages.append(SystemMessage(content="Safety Alert: Company name missing or invalid."))
             
        if not info.description:
            messages.append(SystemMessage(content="Safety Warning: Description is missing."))
            
        if not info.contacts:
             messages.append(SystemMessage(content="Safety Warning: No contacts found."))
             
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a compliance officer. Check if the company operates in any illegal or restricted industries (e.g., weapons, gambling). Respond with 'SAFE' or 'UNSAFE: <reason>'."),
            ("user", "Company: {name}\nDescription: {desc}\nIndustry: {ind}")
        ])
        
        response = self.llm.invoke(prompt.format(
            name=info.name, 
            desc=info.description or "", 
            ind=info.industry or ""
        ))
        
        content = response.content.strip()
        if "UNSAFE" in content.upper():
             messages.append(SystemMessage(content=f"Safety Alert: {content}"))
             
        logger.info(f"SafetyAgent complete. Alerts: {len(messages)}")
        return {"messages": messages}
