import os
import re
from agent.state import AgentState


def sanitize_filename(name: str) -> str:
    """Convert company name to safe filename."""
    # Remove special characters, keep alphanumeric and spaces
    clean = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with underscores
    clean = re.sub(r'\s+', '_', clean)
    # Limit length
    return clean[:100]


def save_file_node(state: AgentState) -> dict:
    """Save the report to a markdown file."""
    company_name = state.get('company_name', 'unknown')
    report = state.get('report', '')

    if not report:
        return {'errors': state.get('errors', []) + ['No report to save']}

    # Create reports directory if needed
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    # Generate filename
    filename = f"{sanitize_filename(company_name)}.md"
    filepath = os.path.join(reports_dir, filename)

    # Write report
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Report saved to: {filepath}")

    return {'report_path': filepath}
