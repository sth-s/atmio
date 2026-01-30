# Company Research Agent Design

**Purpose**: LangGraph agent that researches Italian gas/energy companies and generates sales outreach reports for methane leak detection devices.

## Overview

| Aspect | Decision |
|--------|----------|
| Input | Company name + domain (from CSV) |
| Output | `./reports/{company_name}.md` |
| Stack | LangGraph + Python + BeautifulSoup |
| Data sources | Company website, Ufficio Camerale, Web search (fallback) |
| Contact priority | Sales → Manager → Legal rep → General |
| Report content | Contact + basic company profile |
| Execution | Single company, manual run |

## Architecture

### LangGraph Flow

```
┌─────────────────────┐     ┌───────────────────────┐
│  scrape_website     │     │ scrape_ufficiocamerale│
│  (company domain)   │     │ (legal info)          │
└─────────┬───────────┘     └───────────┬───────────┘
          │                             │
          └──────────┬──────────────────┘
                     ▼
               has_contact?
                │       │
               YES      NO → web_search
                │       │
                ▼       ▼
          ┌──────────────────┐
          │  generate_report │
          └────────┬─────────┘
                   ▼
          ┌──────────────────┐
          │    save_file     │
          └──────────────────┘
```

Both initial scrapes run **in parallel** since they're independent.

### State Schema

```python
class AgentState(TypedDict):
    company_name: str
    domain: str
    scraped_data: dict      # raw website content
    ufficio_data: dict      # legal/official data
    search_results: dict    # web search findings (if used)
    contact: dict           # name, role, email, phone
    company_profile: dict   # size, revenue, employees, year
    report: str             # final markdown
```

## Data Sources

### 1. Company Website Scraping (Primary)

Target pages:
- `/contatti` or `/contact`
- `/chi-siamo` or `/about`
- `/team` or `/staff`
- Footer
- `/impressum` or legal pages

Extract:
- Email addresses (regex: `[\w.-]+@[\w.-]+\.\w+`)
- Phone numbers (Italian format: `+39`, `0X`, etc.)
- Names + roles from team pages

### 2. Ufficio Camerale Scraping

Source: `https://www.ufficiocamerale.it/`

Search by company name, then scrape:
- "Rappresentante Legale" (Legal Representative)
- "Amministratori" (Administrators)
- "Data Costituzione" (Founding date)
- "Capitale Sociale" (Share capital)
- "Stato Attività" (Activity status)
- "Codice ATECO" (Industry code)

### 3. Web Search (Fallback)

Only triggered if no contact found from website + ufficiocamerale.

Search query: `"{company_name}" Italy contact email sales`

## Contact Priority

1. Sales contact from website
2. Other manager from website
3. Legal representative from ufficiocamerale
4. General contact email/phone

## Report Template

**Output file**: `./reports/{company_name}.md`

```markdown
# {Company Name}

## Contact
- **Name**: {contact_name}
- **Role**: {role}
- **Email**: {email}
- **Phone**: {phone}
- **Source**: {website|ufficiocamerale|web_search}

## Company Profile
- **Domain**: {domain}
- **Status**: {active|inactive|in liquidation|...}
- **Founded**: {year}
- **Location**: {city}, Italy
- **Address**: {full_address}
- **Industry**: {ATECO code + description}
- **Share Capital**: {amount}

## Data Sources
- Website: {scraped|failed|no_contact_page}
- Ufficio Camerale: {scraped|not_found}
- Web Search: {used|not_needed}

---
Generated: {timestamp}
```

## Project Structure

```
ag/
├── agent/
│   ├── __init__.py
│   ├── graph.py           # LangGraph definition
│   ├── state.py           # AgentState schema
│   └── nodes/
│       ├── scrape_website.py
│       ├── scrape_ufficiocamerale.py
│       ├── web_search.py
│       ├── generate_report.py
│       └── save_file.py
├── utils/
│   ├── scraper.py         # BeautifulSoup helpers
│   └── extractors.py      # Email/phone regex, contact parsing
├── reports/               # Generated reports go here
├── data/
│   └── companies.csv      # Company list
├── main.py                # CLI entry point
├── requirements.txt
└── .env                   # API keys (Claude, SerpAPI if used)
```

## Dependencies

- `langgraph` - Agent framework
- `langchain-anthropic` - Claude integration
- `beautifulsoup4` + `requests` - Web scraping
- `httpx` - Async HTTP (for parallel scrapes)

## CLI Usage

```bash
python main.py "Vergas S.r.l." --domain vergasmetano.it
```

## Future Enhancements (v2)

- Pain points/hooks: recent leaks, safety violations, regulatory pressure
- Batch mode for processing full CSV
- CRM integration

---

*Design created: 2026-01-30*
