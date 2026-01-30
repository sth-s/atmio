from datetime import datetime
from agent.state import AgentState


def generate_report_node(state: AgentState) -> dict:
    """Generate markdown report from collected data."""
    company_name = state.get('company_name', 'Unknown Company')
    domain = state.get('domain', '')
    contact = state.get('contact', {})
    profile = state.get('company_profile', {})
    scraped_data = state.get('scraped_data', {})
    ufficio_data = state.get('ufficio_data', {})
    search_results = state.get('search_results', {})

    # Build report sections
    lines = [
        f"# {company_name}",
        "",
        "## Contact",
    ]

    if contact:
        lines.extend([
            f"- **Name**: {contact.get('name') or 'N/A'}",
            f"- **Role**: {contact.get('role') or 'N/A'}",
            f"- **Email**: {contact.get('email') or 'N/A'}",
            f"- **Phone**: {contact.get('phone') or 'N/A'}",
            f"- **Source**: {contact.get('source', 'unknown')}",
        ])
    else:
        lines.append("*No contact information found.*")

    lines.extend([
        "",
        "## Company Profile",
        f"- **Domain**: {domain or 'N/A'}",
        f"- **VAT Number**: {profile.get('vat_number') or 'N/A'}",
        f"- **Status**: {profile.get('status') or 'N/A'}",
        f"- **Founded**: {profile.get('founded') or 'N/A'}",
        f"- **Location**: {profile.get('location') or 'N/A'}",
        f"- **Address**: {profile.get('address') or 'N/A'}",
        f"- **Industry (ATECO)**: {profile.get('ateco_code') or 'N/A'}",
        f"- **Share Capital**: {profile.get('share_capital') or 'N/A'}",
    ])

    # Data sources section
    website_status = "scraped" if scraped_data.get('success') else "failed"
    ufficio_status = "scraped" if ufficio_data.get('success') else "not_found"
    search_status = "used" if search_results.get('success') else "not_needed"

    lines.extend([
        "",
        "## Data Sources",
        f"- Website: {website_status} ({scraped_data.get('pages_scraped', 0)} pages)",
        f"- Ufficio Camerale: {ufficio_status}",
        f"- Web Search: {search_status}",
    ])

    # Footer
    lines.extend([
        "",
        "---",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ])

    report = "\n".join(lines)

    return {'report': report}
