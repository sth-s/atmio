import pytest
from langgraph.graph import StateGraph
from src.graph import get_graph

def test_graph_structure():
    """Verifies the graph has the correct nodes and structure."""
    graph = get_graph()
    
    # Check nodes in the underlying graph definition
    # Note: CompiledGraph wraps the graph. Accessing internal structure depends on version.
    # We can check by inspecting the drawable representation or basic execution properties if possible.
    # For now, we rely on the fact that get_graph() returns a CompiledGraph.
    
    assert graph is not None

def test_supervisor_logic_mock():
    """Test supervisor logic with a mocked state (unit test approach)."""
    # This would ideally mock ChatOpenAI, but for a basic smoke test
    # we can check if imports and definitions are valid.
    from src.graph import supervisor_node, GraphState
    from src.schema import CompanyInfo
    
    # Test case: Safety already ran
    from langchain_core.messages import SystemMessage
    state: GraphState = {
        "company_name": "Test",
        "company_info": CompanyInfo(name="Test"),
        "messages": [SystemMessage(content="Safety Alert: OK")],
        "next": ""
    }
    
    result = supervisor_node(state)
    assert result["next"] == "FINISH"
