import os
import logging
from typing import Literal, Dict, Any, Annotated

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END

from src.agents import (
    LegalAgent, ContactAgent, MetricsAgent, SafetyAgent, AgentState
)
from src.schema import CompanyInfo
from src.llm_factory import get_llm

logger = logging.getLogger("atmio.graph")


MAX_ITERATIONS = 10

class GraphState(AgentState):
    next: str
    iterations: int


OPTIONS = ["legal", "contact", "metrics", "safety", "FINISH"]


def supervisor_node(state: GraphState) -> Dict[str, Any]:
    company_info = state.get("company_info")
    iterations = state.get("iterations", 0) + 1
    
    messages = state.get("messages", [])
    safety_run = any("Safety" in m.content for m in messages if isinstance(m, SystemMessage))
    
    if safety_run or iterations > MAX_ITERATIONS:
        logger.info(f"Supervisor: Finishing (safety_run={safety_run}, iterations={iterations})")
        return {"next": "FINISH", "iterations": iterations}

    if not company_info or not company_info.name or company_info.name == "Unknown":
         return {"next": "legal", "iterations": iterations}

    llm = get_llm()

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
4. If you have called an agent and it didn't find anything provided, move to the next step.
5. If all data is present or you have tried everything, call 'safety'.

Respond with ONE word: legal, contact, metrics, safety.
"""),
        ("user", "Who should act next?")
    ])
    
    info_json = company_info.model_dump_json()
    
    try:
        chain = prompt | llm
        response = chain.invoke({"company_info": info_json})
        decision = response.content.strip().replace("'", "").replace('"', "").lower()
        
        if decision not in OPTIONS:
            logger.warning(f"Supervisor LLM returned invalid decision: {decision}. Defaulting to safety.")
            return {"next": "safety", "iterations": iterations}
            
        return {"next": decision, "iterations": iterations}
        
    except Exception as e:
        logger.error(f"Supervisor LLM failed: {e}")
        return {"next": "FINISH", "iterations": iterations}


def get_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("legal", LegalAgent())
    workflow.add_node("contact", ContactAgent())
    workflow.add_node("metrics", MetricsAgent())
    workflow.add_node("safety", SafetyAgent())
    workflow.add_node("supervisor", supervisor_node)

    workflow.add_edge("legal", "supervisor")
    workflow.add_edge("contact", "supervisor")
    workflow.add_edge("metrics", "supervisor")
    workflow.add_edge("safety", "supervisor")

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

    workflow.set_entry_point("supervisor")

    return workflow.compile()
