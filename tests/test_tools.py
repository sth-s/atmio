import pytest
from unittest.mock import MagicMock, patch
from src.tools import TavilySearchWrapper, scrape_with_bs4

@patch('src.tools.TavilyClient')
def test_tavily_search_success(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.search.return_value = {"results": [{"title": "Example", "url": "http://example.com"}]}
    
    wrapper = TavilySearchWrapper(api_key="fake_key")
    results = wrapper.search("test")
    
    assert len(results) == 1
    assert results[0]["title"] == "Example"

@patch('requests.get')
def test_scrape_with_bs4_success(mock_get):
    mock_response = MagicMock()
    mock_response.text = "<html><body><main>Actual Content</main></body></html>"
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    content = scrape_with_bs4("http://example.com")
    assert "Actual Content" in content

@patch('requests.get')
def test_scrape_with_bs4_failure(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.Timeout()
    content = scrape_with_bs4("http://timeout.com")
    assert content is None
