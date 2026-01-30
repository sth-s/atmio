import re
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from agent.state import AgentState


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
}


def search_company_via_ddgs(company_name: str) -> tuple[str | None, dict]:
    """Search for company on ufficiocamerale via DuckDuckGo and extract data from snippets."""
    clean_name = company_name.replace("'", "").replace('"', '')
    query = f'"{clean_name}" site:ufficiocamerale.it'

    url = None
    snippet_data = {}

    try:
        results = DDGS().text(query, max_results=3)
        for r in results:
            href = r.get('href', '')
            title = r.get('title', '')
            body = r.get('body', '')

            # Extract ufficiocamerale URL
            if 'ufficiocamerale.it' in href and not url:
                url = href

            # Extract VAT number from title (format: "Partita IVA: XXXXXXXXXXX")
            vat_match = re.search(r'Partita\s*IVA[:\s]*(\d{11})', title + ' ' + body, re.IGNORECASE)
            if vat_match:
                snippet_data['partita_iva'] = vat_match.group(1)

            # Extract other data from body
            text = title + ' ' + body

            # PEC
            pec_match = re.search(r'PEC[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.it)', text, re.IGNORECASE)
            if pec_match:
                snippet_data['pec'] = pec_match.group(1)

            # ATECO
            ateco_match = re.search(r'ATECO[:\s]+(\d{2,6})', text, re.IGNORECASE)
            if ateco_match:
                snippet_data['ateco'] = ateco_match.group(1)

        return url, snippet_data

    except Exception:
        return None, {}


def extract_from_search_snippets(company_name: str) -> dict:
    """Extract company info from DuckDuckGo search snippets."""
    clean_name = company_name.replace("'", "").replace('"', '')

    queries = [
        f'"{clean_name}" Partita IVA PEC Italia',
        f'"{clean_name}" capitale sociale costituzione',
    ]

    all_text = ""

    try:
        for query in queries:
            results = DDGS().text(query, max_results=5)
            for r in results:
                all_text += r.get('title', '') + ' ' + r.get('body', '') + ' '
    except Exception:
        pass

    if not all_text:
        return {'error': 'No search results'}

    data = {
        'raw_text': all_text[:3000],
        'source': 'search_snippets',
    }

    # Extract fields from combined snippets
    patterns = {
        'partita_iva': r'[Pp]artita\s*IVA[:\s]*(\d{11})',
        'pec': r'PEC[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'founded': r'[Cc]ostitu[ita][aeo][:\s]+(?:il\s+)?(\d{2}/\d{2}/\d{4}|\d{4})',
        'share_capital': r'[Cc]apitale\s+[Ss]ociale[:\s]+([\d.,]+(?:\s*(?:EUR|€))?)',
        'ateco': r'ATECO[:\s]+(\d{2}\.?\d{0,2}\.?\d{0,2})',
        'status': r'[Ss]tato[:\s]+(attiv[ao]|cess?at[ao]|inattiv[ao]|liquidazione)',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            data[field] = match.group(1).strip()

    return data


def scrape_company_page(url: str) -> dict:
    """Scrape company details from ufficiocamerale page (with Cloudflare bypass attempt)."""
    if not url.startswith('http'):
        url = f"https://www.ufficiocamerale.it{url}"

    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get('https://www.ufficiocamerale.it/', timeout=10)
        response = session.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        data = {
            'url': url,
            'raw_text': text[:5000],
        }

        patterns = {
            'legal_representative': r'Rappresentante\s+Legale[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            'administrators': r'Amministrator[ei][:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            'founded': r'Data\s+[Cc]ostituzione[:\s]+(\d{2}/\d{2}/\d{4}|\d{4})',
            'share_capital': r'Capitale\s+[Ss]ociale[:\s]+([\d.,]+\s*(?:EUR|€)?)',
            'status': r'Stato\s+[Aa]ttivit[àa][:\s]+(\w+)',
            'ateco': r'(?:Codice\s+)?ATECO[:\s]+(\d{2}\.?\d{0,2}\.?\d{0,2})',
            'pec': r'PEC[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()

        return data

    except requests.RequestException:
        return {'error': 'Failed to fetch page'}


def scrape_ufficiocamerale_node(state: AgentState) -> dict:
    """Scrape ufficiocamerale.it for official company information."""
    company_name = state.get('company_name', '')

    if not company_name:
        return {
            'ufficio_data': {'success': False, 'error': 'No company name provided'},
        }

    data = {}

    # Try 1: Search via DDGS and get data from snippets
    detail_url, snippet_data = search_company_via_ddgs(company_name)

    # Merge snippet data
    if snippet_data:
        data.update(snippet_data)

    # Try 2: If we have a URL, try to scrape the page (might fail due to Cloudflare)
    if detail_url:
        page_data = scrape_company_page(detail_url)
        if 'error' not in page_data:
            # Page scraping succeeded, merge data
            data.update(page_data)

    # Try 3: If still no data, try general search snippets
    if not data or (not data.get('partita_iva') and not data.get('pec')):
        extra_data = extract_from_search_snippets(company_name)
        if 'error' not in extra_data:
            # Merge without overwriting existing data
            for k, v in extra_data.items():
                if k not in data or not data[k]:
                    data[k] = v

    if not data or 'error' in data:
        return {
            'ufficio_data': {'success': False, 'error': data.get('error', 'No data found')},
        }

    result = {
        'ufficio_data': {
            'success': True,
            **data,
        },
    }

    # Build company profile from ufficio data
    profile = {}
    if data.get('status'):
        profile['status'] = data['status']
    if data.get('founded'):
        profile['founded'] = data['founded']
    if data.get('share_capital'):
        profile['share_capital'] = data['share_capital']
    if data.get('ateco'):
        profile['ateco_code'] = data['ateco']
    if data.get('partita_iva'):
        profile['vat_number'] = data['partita_iva']

    if profile:
        existing_profile = state.get('company_profile', {})
        result['company_profile'] = {**existing_profile, **profile}

    # If we found a legal representative and don't have a contact yet, use it
    if data.get('legal_representative') and not state.get('contact'):
        result['contact'] = {
            'name': data['legal_representative'],
            'role': 'Rappresentante Legale',
            'email': data.get('pec', ''),
            'phone': '',
            'source': 'ufficiocamerale',
        }
        result['has_contact'] = True

    # If we found PEC but no contact email, add it
    if data.get('pec') and not state.get('contact', {}).get('email'):
        existing_contact = state.get('contact', {})
        result['contact'] = {
            **existing_contact,
            'email': data['pec'],
            'source': existing_contact.get('source', 'ufficiocamerale'),
        }

    return result
