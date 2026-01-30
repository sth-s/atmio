import logging
import os
import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from tavily import TavilyClient

# Configure logging according to skill guidance
# Configure logging according to skill guidance
# logging.basicConfig removed - relying on root logger from main.py
logger = logging.getLogger("atmio.tools")

class TavilySearchWrapper:
    """
    A robust wrapper for the TavilySearch API.
    Handles API key configuration and error management.
    """
    def __init__(self, api_key: Optional[str] = None):
        # Config: prefer explicit key, then env var
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.error("TAVILY_API_KEY not found. Search functionality will be unavailable.")
            self.client = None
        else:
            self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, max_results: int = 5, search_depth: str = "advanced") -> List[Dict[str, Any]]:
        """
        Executes a search query using Tavily and returns a list of result dictionaries.
        """
        if not self.client:
            logger.error("Tavily client not initialized.")
            return []
            
        try:
            logger.info(f"Tavily Search: {query} (limit={max_results})")
            response = self.client.search(
                query=query, 
                max_results=max_results, 
                search_depth=search_depth
            )
            results = response.get("results", [])
            logger.info(f"Tavily found {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Tavily search error for '{query}': {str(e)}")
            return []

def scrape_with_bs4(url: str, timeout: int = 15) -> Optional[str]:
    """
    Scrapes the text content of a webpage using requests and BeautifulSoup.
    
    Rules followed:
    - Explicit timeout (15s default)
    - Error handling for network/HTTP issues
    - Basic HTML cleaning (removes scripts/styles/nav/footers)
    """
    try:
        logger.info(f"Scraping content from: {url}")
        # Standard headers to avoid 403 Forbidden on some sites
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        # Centralized request sending with timeout
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Decompose non-content elements to reduce noise
        for element in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
            element.decompose()
            
        # Extract and clean text
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        logger.info(f"Scraping successful for {url}. Extracted {len(clean_text)} characters.")
        return clean_text
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while scraping {url}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} while scraping {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected scraping error for {url}: {str(e)}")
        
    return None
