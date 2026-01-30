from typing import TypedDict, Optional


class Contact(TypedDict, total=False):
    name: str
    role: str
    email: str
    phone: str
    source: str  # website | ufficiocamerale | web_search


class CompanyProfile(TypedDict, total=False):
    domain: str
    status: str
    founded: str
    location: str
    address: str
    industry: str
    ateco_code: str
    share_capital: str


class AgentState(TypedDict, total=False):
    # Input
    company_name: str
    domain: str

    # Scraped data
    scraped_data: dict
    ufficio_data: dict
    search_results: dict

    # Processed output
    contact: Contact
    company_profile: CompanyProfile

    # Final report
    report: str

    # Status flags
    has_contact: bool
    errors: list[str]
