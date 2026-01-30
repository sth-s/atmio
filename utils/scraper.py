import requests
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

CONTACT_PATHS = [
    '/contatti',
    '/contact',
    '/contatti/',
    '/contact/',
    '/chi-siamo',
    '/about',
    '/chi-siamo/',
    '/about-us',
    '/team',
    '/staff',
    '/azienda',
    '/company',
]


def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch a page and return its HTML content."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML into BeautifulSoup object."""
    return BeautifulSoup(html, 'html.parser')


def extract_text(soup: BeautifulSoup) -> str:
    """Extract readable text from parsed HTML."""
    # Only remove scripts and styles, keep footer/header for contact info
    for element in soup(['script', 'style']):
        element.decompose()
    return soup.get_text(separator=' ', strip=True)


def extract_mailto_links(soup: BeautifulSoup) -> list[str]:
    """Extract email addresses from mailto links."""
    emails = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('mailto:'):
            email = href.replace('mailto:', '').split('?')[0]
            if email:
                emails.append(email)
    return emails


def extract_tel_links(soup: BeautifulSoup) -> list[str]:
    """Extract phone numbers from tel links."""
    phones = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('tel:'):
            # Handle both tel: and tel:// formats
            phone = href.replace('tel://', '').replace('tel:', '').strip()
            if phone:
                phones.append(phone)
    return phones


def find_contact_pages(base_url: str) -> list[str]:
    """Generate list of potential contact page URLs."""
    if not base_url.startswith('http'):
        base_url = f'https://{base_url}'

    return [urljoin(base_url, path) for path in CONTACT_PATHS]


def scrape_website(domain: str) -> dict:
    """Scrape a company website for contact information."""
    base_url = f'https://{domain}' if not domain.startswith('http') else domain

    result = {
        'homepage': None,
        'contact_pages': [],
        'all_text': '',
        'mailto_emails': [],
        'tel_phones': [],
        'success': False,
    }

    # Fetch homepage
    homepage_html = fetch_page(base_url)
    if homepage_html:
        result['homepage'] = homepage_html
        soup = parse_html(homepage_html)
        result['all_text'] += extract_text(soup) + ' '
        result['mailto_emails'].extend(extract_mailto_links(soup))
        result['tel_phones'].extend(extract_tel_links(soup))
        result['success'] = True

    # Fetch contact pages
    for url in find_contact_pages(base_url):
        html = fetch_page(url)
        if html:
            result['contact_pages'].append({
                'url': url,
                'html': html,
            })
            soup = parse_html(html)
            result['all_text'] += extract_text(soup) + ' '
            result['mailto_emails'].extend(extract_mailto_links(soup))
            result['tel_phones'].extend(extract_tel_links(soup))

    # Deduplicate
    result['mailto_emails'] = list(set(result['mailto_emails']))
    result['tel_phones'] = list(set(result['tel_phones']))

    return result


def extract_team_members(soup: BeautifulSoup) -> list[dict]:
    """Try to extract team member info from a page."""
    members = []

    # Common patterns for team sections
    team_containers = soup.find_all(['div', 'section'], class_=lambda x: x and any(
        kw in x.lower() for kw in ['team', 'staff', 'people', 'membri']
    ) if x else False)

    for container in team_containers:
        # Look for individual member cards
        cards = container.find_all(['div', 'article'], class_=lambda x: x and any(
            kw in x.lower() for kw in ['member', 'person', 'card', 'profile']
        ) if x else False)

        for card in cards:
            name_elem = card.find(['h2', 'h3', 'h4', 'strong', 'span'])
            role_elem = card.find(['p', 'span'], class_=lambda x: x and 'role' in x.lower() if x else False)

            if name_elem:
                members.append({
                    'name': name_elem.get_text(strip=True),
                    'role': role_elem.get_text(strip=True) if role_elem else None,
                })

    return members
