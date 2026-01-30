import os
import logging
from typing import Literal, Dict, Any, Annotated

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END

from src.agents import (
    LegalAgent, ContactAgent, MetricsAgent, SafetyAgent, AgentState
)
from src.schema import CompanyInfo

logger = logging.getLogger("atmio.graph")

# Define a state that includes the 'next' field for routing
class GraphState(AgentState):
    next: str

# Options for the supervisor
OPTIONS = ["legal", "contact", "metrics", "safety"]

def supervisor_node(state: GraphState) -> Dict[str, Any]:
    """
    The supervisor node decides which agent should act next or if the process is finished.
    """
    company_info = state.get("company_info")
    
    # 1. Immediate termination check: If safety has run, we are done.
    # We check if any SystemMessage contains "Safety Alert" or just comes from SafetyAgent
    messages = state.get("messages", [])
    # Heuristic: SafetyAgent produces messages starting with "Safety"
    safety_run = any("Safety" in m.content for m in messages if isinstance(m, SystemMessage))
    
    if safety_run:
        logger.info("Supervisor: Safety check complete. Finishing.")
        return {"next": "FINISH"}

    # 2. Heuristic checks for missing critical data (Fallback/Fast-path)
    if not company_info or not company_info.name or company_info.name == "Unknown":
         return {"next": "legal"}

    # 3. LLM Decision for orchestration
    llm = ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a research supervisor managing a team of agents:
- legal: Extracts company name, description, industry, website.
- contact: Extracts key contacts.
- metrics: Extracts financial metrics.
- safety: Validates data and checks compliance.

Your goal is to fully enrich the CompanyInfo.
Current State:
{company_info}

Decide who should act next.
Rules:
1. If basic info (description, website) is missing, call 'legal'.
2. If contacts are missing, call 'contact'.
3. If metrics are missing, call 'metrics'.
4. If all data is present, call 'safety' to validate.

Respond with ONE word: legal, contact, metrics, safety.
"""),
        ("user", "Who should act next?")
    ])
    
    # Serialize info for prompt
    info_json = company_info.model_dump_json()
    
    try:
        chain = prompt | llm
        response = chain.invoke({"company_info": info_json})
        decision = response.content.strip().replace("'", "").replace('"', "").lower()
        
        if decision not in OPTIONS:
            logger.warning(f"Supervisor LLM returned invalid decision: {decision}. Defaulting to safety.")
            return {"next": "safety"}
            
        return {"next": decision}
        
    except Exception as e:
        logger.error(f"Supervisor LLM failed: {e}")
        return {"next": "FINISH"}

def get_graph():
    """Builds and returns the StateGraph."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("legal", LegalAgent())
    workflow.add_node("contact", ContactAgent())
    workflow.add_node("metrics", MetricsAgent())
    workflow.add_node("safety", SafetyAgent())
    workflow.add_node("supervisor", supervisor_node)

    # Edges: Workers return to supervisor
    workflow.add_edge("legal", "supervisor")
    workflow.add_edge("contact", "supervisor")
    workflow.add_edge("metrics", "supervisor")
    workflow.add_edge("safety", "supervisor")

    # Conditional edge from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next"],
        {
            "legal": "legal",
            "contact": "contact",
            "metrics": "metrics",
            "safety": "safety",
            "FINISH": END
        }
    )

    # Entry point
    workflow.set_entry_point("supervisor")

    return workflow.compile()
