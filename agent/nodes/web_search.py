import os
import requests
from agent.state import AgentState
from utils.extractors import extract_emails, extract_phones


def web_search_node(state: AgentState) -> dict:
    """Search the web for company contact information as fallback."""
    company_name = state.get('company_name', '')

    if not company_name:
        return {
            'search_results': {'success': False, 'error': 'No company name'},
        }

    # For now, we'll use a simple approach with DuckDuckGo HTML
    # In production, you'd use SerpAPI or similar
    query = f"{company_name} Italy contact email sales manager"

    try:
        # Using DuckDuckGo HTML version (no API key needed)
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        text = response.text

        # Extract any emails/phones from search results
        emails = extract_emails(text)
        phones = extract_phones(text)

        result = {
            'search_results': {
                'success': True,
                'query': query,
                'emails_found': emails[:5],  # Limit results
                'phones_found': phones[:5],
            },
        }

        # If we still don't have a contact and found emails, use them
        if not state.get('contact') and emails:
            result['contact'] = {
                'name': '',
                'role': '',
                'email': emails[0],
                'phone': phones[0] if phones else '',
                'source': 'web_search',
            }
            result['has_contact'] = True

        return result

    except requests.RequestException as e:
        return {
            'search_results': {'success': False, 'error': str(e)},
        }
