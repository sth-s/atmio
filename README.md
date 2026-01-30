# Gas Company Data Enrichment Agent

A hierarchical multi-agent system built with `langgraph` to enrich Italian gas distribution company data.

## Features
- **Hierarchical Agents**: Supervisor routes tasks to specialized workers (Legal, Contact, Metrics, Safety).
- **Tools**: Web scraping (`requests`, `bs4`) and Search (`Tavily`).
- **Resilience**: Handles errors, recursion limits, and robust data merging.

## Prerequisites
- Python 3.9+
- API Keys:
    - [OpenRouter](https://openrouter.ai/) (for LLM)
    - [Tavily](https://tavily.com/) (for Search)

## Setup

1.  **Create Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Copy the example file and add your keys:
    ```bash
    cp .env.example .env
    # Edit .env with your actual keys
    nano .env
    ```

## Usage

### Test Run (Dry Run)
Process only the first row to verify setup:
```bash
python main.py --limit 1
```

### Full Execution
Process the entire `data.csv`:
```bash
python main.py
```

## Output
Results are written to `data_enriched.csv`.
- **Original Columns**: Preserved.
- **processing_status**: `SUCCESS`, `ERROR`, etc.
- **enriched_data**: JSON string containing the extracted `CompanyInfo` (Contacts, Metrics, etc.).

## Project Structure
- `src/`: Agent code.
    - `agents.py`: Worker agent definitions.
    - `graph.py`: Supervisor and graph routing.
    - `tools.py`: Search and scraper tools.
    - `schema.py`: Data models.
- `main.py`: Entry point.
- `data.csv`: Input file.