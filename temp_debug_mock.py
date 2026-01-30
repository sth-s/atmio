from unittest.mock import MagicMock, patch
from src.schema import CompanyInfo
from src.agents import LegalAgent

# Mocking external dependencies manually to simulate test environment
with patch("src.agents.ChatOpenAI") as MockChatOpenAI, \
     patch("src.agents.TavilySearchWrapper") as MockTavily:
    
    # Analyze what MockChatOpenAI returns
    print(f"MockChatOpenAI: {MockChatOpenAI}")
    mock_llm = MockChatOpenAI.return_value
    print(f"mock_llm (instance): {mock_llm}")
    
    # Configure the mock
    expected_info = CompanyInfo(
        name="Test Corp", description="A tech company", industry="Tech", website="http://test.com"
    )
    # Trying to match test_agents.py setup
    # ALSO set return_value for __call__ in case LangChain treats it as a callable
    mock_llm.with_structured_output.return_value.return_value = expected_info
    mock_llm.with_structured_output.return_value.invoke.return_value = expected_info
    
    # Instantiate Agent
    print("Instantiating LegalAgent...")
    agent = LegalAgent()
    
    # Check if agent.llm is indeed mock_llm
    print(f"agent.llm: {agent.llm}")
    print(f"Is agent.llm same as mock_llm? {agent.llm is mock_llm}")
    
    # Run the agent logic manually
    state = {"company_name": "Test Corp", "messages": []}
    
    # Mocking Tavily search
    MockTavily.return_value.search.return_value = [{"title": "T", "content": "C", "url": "U"}]
    
    print("Running agent...")
    result = agent(state)
    print(f"Result: {result}")
    
    # Check what invoke returned
    if "company_info" in result:
        print(f"Result info: {result['company_info']}")
        print(f"Result info type: {type(result['company_info'])}")
        print(f"Result info name: {result['company_info'].name}")
    else:
        print("No company_info in result")
