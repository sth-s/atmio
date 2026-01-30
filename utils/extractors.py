import re
from typing import Optional


def extract_emails(text: str) -> list[str]:
    """Extract email addresses from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    # Filter out common false positives
    excluded = {'example.com', 'domain.com', 'email.com'}
    return [e for e in emails if not any(ex in e for ex in excluded)]


def extract_phones(text: str) -> list[str]:
    """Extract Italian phone numbers from text."""
    patterns = [
        r'\+39[\s.-]?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}',  # +39 format
        r'0\d{1,3}[\s.-]?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{0,4}',  # 0X landline (spaced)
        r'3\d{2}[\s.-]?\d{2,4}[\s.-]?\d{2,4}',  # 3XX mobile format
    ]
    phones = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        # Clean up: remove extra whitespace
        phones.extend([re.sub(r'\s+', ' ', m).strip() for m in matches])
    return list(set(phones))


def extract_contact_from_text(text: str, html_content: str = "") -> dict:
    """Extract contact info from page text."""
    emails = extract_emails(text)
    phones = extract_phones(text)

    return {
        'emails': emails,
        'phones': phones,
    }


def classify_email(email: str) -> str:
    """Classify email by likely department."""
    email_lower = email.lower()

    if any(kw in email_lower for kw in ['sales', 'vendite', 'commercial']):
        return 'sales'
    elif any(kw in email_lower for kw in ['info', 'contatti', 'contact']):
        return 'general'
    elif any(kw in email_lower for kw in ['admin', 'direzione', 'management']):
        return 'management'
    elif any(kw in email_lower for kw in ['support', 'assistenza', 'help']):
        return 'support'
    else:
        return 'unknown'


def prioritize_contacts(contacts: list[dict]) -> Optional[dict]:
    """Select best contact based on priority: sales > manager > general."""
    if not contacts:
        return None

    priority_order = ['sales', 'management', 'general', 'unknown', 'support']

    for priority in priority_order:
        for contact in contacts:
            if contact.get('type') == priority:
                return contact

    return contacts[0] if contacts else None
