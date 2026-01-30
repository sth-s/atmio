import unittest
from unittest.mock import MagicMock, patch
from src.schema import CompanyInfo, Contact, Metrics
from src.agents import LegalAgent, ContactAgent, MetricsAgent, SafetyAgent, AgentState

class TestAgents(unittest.TestCase):

    def setUp(self):
        # Common mocks
        self.mock_llm_response = MagicMock()
        self.mock_tavily_search = MagicMock(return_value=[
            {"title": "Test Corp", "content": "Test Corp is a tech company.", "url": "http://test.com"}
        ])

    @patch("src.agents.ChatOpenAI")
    @patch("src.agents.TavilySearchWrapper")
    def test_legal_agent(self, MockTavily, MockChatOpenAI):
        # Setup
        mock_llm = MockChatOpenAI.return_value
        mock_llm.with_structured_output.return_value.invoke.return_value = CompanyInfo(
            name="Test Corp", description="A tech company", industry="Tech", website="http://test.com"
        )
        MockTavily.return_value.search = self.mock_tavily_search
        
        agent = LegalAgent()
        state = {"company_name": "Test Corp", "company_info": None, "messages": []}
        
        # Execute
        result = agent(state)
        
        # Assert
        self.assertIn("company_info", result)
        self.assertEqual(result["company_info"].name, "Test Corp")
        self.assertEqual(result["company_info"].industry, "Tech")

    @patch("src.agents.ChatOpenAI")
    @patch("src.agents.TavilySearchWrapper")
    def test_contact_agent(self, MockTavily, MockChatOpenAI):
        # Setup
        mock_llm = MockChatOpenAI.return_value
        # Mocking the inner Pydantic model response
        mock_contacts_result = MagicMock()
        mock_contacts_result.contacts = [Contact(name="Alice", role="CEO")]
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_contacts_result
        
        MockTavily.return_value.search = self.mock_tavily_search
        
        agent = ContactAgent()
        state = {
            "company_name": "Test Corp", 
            "company_info": CompanyInfo(name="Test Corp"), 
            "messages": []
        }
        
        # Execute
        result = agent(state)
        
        # Assert
        self.assertIn("company_info", result)
        self.assertEqual(len(result["company_info"].contacts), 1)
        self.assertEqual(result["company_info"].contacts[0].name, "Alice")

    @patch("src.agents.ChatOpenAI")
    @patch("src.agents.TavilySearchWrapper")
    def test_metrics_agent(self, MockTavily, MockChatOpenAI):
        # Setup
        mock_llm = MockChatOpenAI.return_value
        mock_llm.with_structured_output.return_value.invoke.return_value = Metrics(revenue=1000000, employees=50)
        MockTavily.return_value.search = self.mock_tavily_search
        
        agent = MetricsAgent()
        state = {
            "company_name": "Test Corp", 
            "company_info": CompanyInfo(name="Test Corp"), 
            "messages": []
        }
        
        # Execute
        result = agent(state)
        
        # Assert
        self.assertIn("company_info", result)
        self.assertEqual(result["company_info"].metrics.employees, 50)

    @patch("src.agents.ChatOpenAI")
    def test_safety_agent(self, MockChatOpenAI):
        # Setup
        mock_llm = MockChatOpenAI.return_value
        mock_llm.invoke.return_value.content = "SAFE"
        
        agent = SafetyAgent()
        state = {
            "company_name": "Test Corp",
            "company_info": CompanyInfo(
                name="Test Corp", 
                description="Legit business", 
                contacts=[Contact(name="Bob")]
            ),
            "messages": []
        }
        
        # Execute
        result = agent(state)
        
        # Assert
        self.assertIn("messages", result)
        # Should be empty if safe
        self.assertEqual(len(result["messages"]), 0)

if __name__ == "__main__":
    unittest.main()
