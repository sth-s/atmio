from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.scrape_website import scrape_website_node
from agent.nodes.scrape_ufficiocamerale import scrape_ufficiocamerale_node
from agent.nodes.web_search import web_search_node
from agent.nodes.generate_report import generate_report_node
from agent.nodes.save_file import save_file_node


def should_web_search(state: AgentState) -> str:
    """Decide whether to run web search based on contact availability."""
    if state.get('has_contact') and state.get('contact', {}).get('email'):
        return "generate_report"
    return "web_search"


def create_graph() -> StateGraph:
    """Create the company research agent graph."""

    # Initialize graph with state schema
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("scrape_website", scrape_website_node)
    graph.add_node("scrape_ufficiocamerale", scrape_ufficiocamerale_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("save_file", save_file_node)

    # Set entry point - both scrapes run first
    graph.set_entry_point("scrape_website")

    # Add edges
    # After website scrape, go to ufficiocamerale
    graph.add_edge("scrape_website", "scrape_ufficiocamerale")

    # After ufficiocamerale, conditionally go to web_search or generate_report
    graph.add_conditional_edges(
        "scrape_ufficiocamerale",
        should_web_search,
        {
            "web_search": "web_search",
            "generate_report": "generate_report",
        }
    )

    # After web_search, go to generate_report
    graph.add_edge("web_search", "generate_report")

    # After generate_report, save file
    graph.add_edge("generate_report", "save_file")

    # After save_file, end
    graph.add_edge("save_file", END)

    return graph


def build_agent():
    """Build and compile the agent."""
    graph = create_graph()
    return graph.compile()
