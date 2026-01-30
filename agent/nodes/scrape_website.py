from agent.state import AgentState
from utils.scraper import scrape_website, parse_html, extract_team_members
from utils.extractors import extract_contact_from_text, classify_email


def scrape_website_node(state: AgentState) -> dict:
    """Scrape the company's own website for contact information."""
    domain = state.get('domain', '')
    company_name = state.get('company_name', '')

    if not domain:
        return {
            'scraped_data': {'success': False, 'error': 'No domain provided'},
            'errors': state.get('errors', []) + ['No domain provided for website scraping'],
        }

    scraped = scrape_website(domain)

    contacts = []
    team_members = []

    # First, add mailto and tel links (most reliable)
    for email in scraped.get('mailto_emails', []):
        email_type = classify_email(email)
        contacts.append({
            'email': email,
            'type': email_type,
            'source': 'website',
        })

    for phone in scraped.get('tel_phones', []):
        contacts.append({
            'phone': phone,
            'type': 'unknown',
            'source': 'website',
        })

    # Then extract from page text (fallback)
    if scraped.get('all_text'):
        contact_info = extract_contact_from_text(scraped['all_text'])

        for email in contact_info.get('emails', []):
            # Skip if already found via mailto
            if any(c.get('email') == email for c in contacts):
                continue
            email_type = classify_email(email)
            contacts.append({
                'email': email,
                'type': email_type,
                'source': 'website',
            })

        for phone in contact_info.get('phones', []):
            # Skip if already found via tel link
            if any(c.get('phone') == phone for c in contacts):
                continue
            contacts.append({
                'phone': phone,
                'type': 'unknown',
                'source': 'website',
            })

    # Try to extract team members from contact pages
    for page in scraped.get('contact_pages', []):
        soup = parse_html(page['html'])
        members = extract_team_members(soup)
        team_members.extend(members)

    # Check if we found any contact
    has_contact = bool(contacts) or bool(team_members)

    result = {
        'scraped_data': {
            'success': scraped.get('success', False),
            'contacts': contacts,
            'team_members': team_members,
            'pages_scraped': len(scraped.get('contact_pages', [])) + (1 if scraped.get('homepage') else 0),
        },
    }

    # Set has_contact flag if we have usable contacts
    if has_contact:
        result['has_contact'] = True

        # Try to build best contact from scraped data
        best_email = None
        best_phone = None

        # Prioritize sales emails
        for c in contacts:
            if 'email' in c:
                if c.get('type') == 'sales':
                    best_email = c['email']
                    break
                elif not best_email:
                    best_email = c['email']

        for c in contacts:
            if 'phone' in c:
                best_phone = c['phone']
                break

        # Get best team member name
        best_name = None
        best_role = None
        for member in team_members:
            if member.get('name'):
                best_name = member['name']
                best_role = member.get('role')
                break

        if best_email or best_phone or best_name:
            result['contact'] = {
                'name': best_name or '',
                'role': best_role or '',
                'email': best_email or '',
                'phone': best_phone or '',
                'source': 'website',
            }

    return result
