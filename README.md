# Company Research Agent

LangGraph agent that researches Italian gas/energy companies and generates sales reports for methane leak detection device outreach.

## Architecture

```
┌─────────────────────┐     ┌───────────────────────┐
│  scrape_website     │     │ scrape_ufficiocamerale│
│  (company domain)   │     │ (legal/official data) │
└─────────┬───────────┘     └───────────┬───────────┘
          │                             │
          └──────────┬──────────────────┘
                     ▼
               has_contact?
                │       │
               YES      NO
                │       │
                │       ▼
                │  ┌─────────────┐
                │  │ web_search  │
                │  └─────┬───────┘
                │        │
                ▼        ▼
          ┌──────────────────┐
          │  generate_report │
          └────────┬─────────┘
                   ▼
          ┌──────────────────┐
          │    save_file     │
          └──────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | LangGraph |
| Web Scraping | BeautifulSoup4, requests |
| Search | ddgs (DuckDuckGo) |
| Language | Python 3.10+ |

## Nodes

### scrape_website
Scrapes the company's own website for contact information.
- Fetches homepage + contact pages (`/contatti`, `/chi-siamo`, `/team`, etc.)
- Extracts emails from `mailto:` links and text patterns
- Extracts phones from `tel:` links and Italian number patterns
- Attempts to find team member names and roles

### scrape_ufficiocamerale
Retrieves official Italian business registry data.
- Searches via DuckDuckGo for `site:ufficiocamerale.it`
- Extracts from search snippets: VAT number (Partita IVA), PEC email, ATECO code
- Falls back to general search if site-specific search fails
- Bypasses Cloudflare protection by using search snippets

### web_search
Fallback search when no contact found from other sources.
- Searches DuckDuckGo for company contact information
- Only triggered if `scrape_website` and `scrape_ufficiocamerale` didn't find contacts

### generate_report
Compiles all collected data into a markdown report.

### save_file
Saves the report to `./reports/{company_name}.md`

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment (optional, for future Claude integration)
cp .env.example .env
```

## Usage

### Batch Mode (Process All Companies)

```bash
# Process all companies from CSV
python main.py

# Process first N companies
python main.py --limit 10

# Custom delay between requests (default: 2 sec)
python main.py --delay 3

# Use different CSV file
python main.py --csv path/to/companies.csv
```

### Single Company Mode

```bash
# Research a specific company (looks up in CSV for domain)
python main.py "Butan Gas S.p.a."

# With explicit domain
python main.py "Custom Company" --domain example.it
```

## Input Data

CSV file with columns:
- `Unternehmensname` - Company name
- `Domainname des Unternehmens` - Company domain
- `Stadt` - City
- `Adresszeile` - Address
- `Branche` - Industry

## Output

Reports saved to `./reports/{company_name}.md`:

```markdown
# Company Name

## Contact
- **Name**: Contact Person
- **Role**: Sales Manager
- **Email**: contact@company.it
- **Phone**: 02 1234567
- **Source**: website

## Company Profile
- **Domain**: company.it
- **VAT Number**: 12345678901
- **Status**: Attiva
- **Founded**: 2010
- **Location**: Milano
- **Industry (ATECO)**: 35.22

## Data Sources
- Website: scraped (5 pages)
- Ufficio Camerale: scraped
- Web Search: not_needed
```

## Project Structure

```
ag/
├── agent/
│   ├── graph.py              # LangGraph workflow definition
│   ├── state.py              # State schema (TypedDict)
│   └── nodes/
│       ├── scrape_website.py
│       ├── scrape_ufficiocamerale.py
│       ├── web_search.py
│       ├── generate_report.py
│       └── save_file.py
├── utils/
│   ├── scraper.py            # Web scraping utilities
│   └── extractors.py         # Email/phone extraction
├── data/
│   └── companies.csv         # Input company list
├── reports/                  # Generated reports
├── main.py                   # CLI entry point
└── requirements.txt
```

## Contact Priority

The agent prioritizes contacts in this order:
1. Sales contact from website
2. Other manager from website
3. Legal representative from Ufficio Camerale
4. General contact (info@ email, main phone)
