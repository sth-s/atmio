import logging
import os
import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from tavily import TavilyClient

logger = logging.getLogger("atmio.tools")


class TavilySearchWrapper:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.error("TAVILY_API_KEY not found. Search functionality will be unavailable.")
            self.client = None
        else:
            self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, max_results: int = 5, search_depth: str = "advanced") -> List[Dict[str, Any]]:
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


def scrape_with_bs4(url: str, timeout: int = 20) -> Optional[str]:
    try:
        logger.info(f"Scraping content from: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
            element.decompose()
            
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


def scrape_ufficiocamerale(company_name: str) -> Optional[str]:
    from urllib.parse import quote
    encoded_name = quote(company_name)
    url = f"https://www.ufficiocamerale.it/cerca/{encoded_name}"
    logger.info(f"Scraping ufficiocamerale for: {company_name}")
    return scrape_with_bs4(url)


def scrape_arera(company_name: str) -> Optional[str]:
    # ARERA search is more complex, usually requires specific parameters. 
    # For now, we'll try a Google search specifically targeting ARERA or a known search URL if available.
    # ARERA's official search is: https://www.arera.it/ricerca?q=...
    from urllib.parse import quote
    encoded_name = quote(company_name)
    url = f"https://www.arera.it/ricerca?q={encoded_name}"
    logger.info(f"Scraping Arera for: {company_name}")
    content = scrape_with_bs4(url)
    if content:
         return f"ARERA Search Results for {company_name}:\n{content[:5000]}"
    return None


def scrape_website_contacts(url: str) -> Optional[str]:
    """Tries to find and scrape contact pages like /contatti, /contact, etc."""
    base_url = url.rstrip("/")
    candidates = ["/contatti", "/contacts", "/contact", "/chi-siamo", "/about-us"]
    
    # First try main page
    content = scrape_with_bs4(url)
    if content:
        import re
        # Basic check for emails in main page
        if re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content):
            return content

    for path in candidates:
        target = f"{base_url}{path}"
        logger.info(f"Checking contact page: {target}")
        page_content = scrape_with_bs4(target)
        if page_content:
             return page_content
             
    return None
