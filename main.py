import os
import sys
import csv
import logging
import argparse
import uuid
import json
from typing import List, Dict, Any

# Attempt to load dotenv, warn if missing
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Ensure src can be imported
sys.path.append(os.getcwd())

from langgraph.errors import GraphRecursionError
from src.graph import get_graph
from src.schema import CompanyInfo

def setup_logging(run_id: str):
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    log_level = logging.DEBUG if dev_mode else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format=f'%(asctime)s [{run_id}] %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("main")


def load_csv(filepath: str) -> List[Dict[str, str]]:
    """Reads CSV into a list of dictionaries."""
    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f: # utf-8-sig for Excel compatibility
            return list(csv.DictReader(f))
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        sys.exit(1)

def save_csv(filepath: str, data: List[Dict[str, Any]], fieldnames: List[str]):
    """Writes list of dictionaries to CSV."""
    # Ensure all fieldnames are present in data rows (fill with empty string if missing)
    for row in data:
        for field in fieldnames:
            if field not in row:
                row[field] = ""

    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

# --- Main Logic ---

def process_row(row: Dict[str, str], graph: Any) -> Dict[str, Any]:
    """Process a single row through the agent graph."""
    company_name = row.get("Unternehmensname", "Unknown")
    domain = row.get("Domainname des Unternehmens", "").strip()
    industry = row.get("Branche", "").strip()
    
    # 1. Map CSV fields to Initial State
    initial_info = CompanyInfo(
        name=company_name,
        website=domain if domain else None,
        industry=industry if industry else None
    )
    
    state = {
        "company_name": company_name,
        "company_info": initial_info,
        "messages": []
    }
    
    # 2. Invoke Graph
    try:
        # Recursion limit handles infinite loops (agent ping-pong)
        # We use a reasonably high limit as the supervisor might iterate a few times
        result = graph.invoke(state, config={"recursion_limit": 20})
        
        return {
            "status": "SUCCESS",
            "error": None,
            "company_info": result.get("company_info")
        }
        
    except GraphRecursionError:
        logger.warning(f"Recursion limit reached for {company_name}")
        return {
            "status": "RECURSION_LIMIT",
            "error": "GraphRecursionError",
            "company_info": None 
        }
    except Exception as e:
        logger.error(f"Error processing {company_name}: {e}")
        return {
            "status": "ERROR",
            "error": str(e),
            "company_info": None
        }

def main():
    parser = argparse.ArgumentParser(description="Enrich company data using Agent Graph.")
    parser.add_argument("--limit", type=int, help="Limit number of rows to process (for testing)")
    parser.add_argument("--input", default="data.csv", help="Input CSV file path")
    parser.add_argument("--output", default="data_enriched.csv", help="Output CSV file path")
    args = parser.parse_args()

    # 1. Load env first so DEV_MODE is available for logging
    if load_dotenv:
        load_dotenv()
    
    run_id = str(uuid.uuid4())[:8]
    setup_logging(run_id)
    
    if not load_dotenv:
        logger.warning("python-dotenv not installed. Relying on existing env vars.")

    # 2. Load Data
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Reading from {args.input}")
    raw_data = load_csv(args.input)
    
    if args.limit:
        logger.info(f"Limiting to first {args.limit} rows.")
        raw_data = raw_data[:args.limit]
        
    logger.info(f"Rows to process: {len(raw_data)}")
    
    # 3. Initialize Graph
    try:
        logger.info("Initializing Agent Graph...")
        graph = get_graph()
    except Exception as e:
        logger.critical(f"Failed to compile graph: {e}")
        sys.exit(1)

    # 4. Processing Loop
    enriched_results = []
    stats = {"processed": 0, "success": 0, "failed": 0}
    
    # Determine output headers
    # We keep original columns and add status + enriched_json
    if raw_data:
        fieldnames = list(raw_data[0].keys()) + ["processing_status", "processing_error", "enriched_data"]
    else:
        fieldnames = ["processing_status", "processing_error", "enriched_data"]

    for i, row in enumerate(raw_data):
        stats["processed"] += 1
        logger.info(f"[{i+1}/{len(raw_data)}] Processing: {row.get('Unternehmensname')}")
        
        result = process_row(row, graph)
        
        # Prepare Output Row
        out_row = row.copy()
        out_row["processing_status"] = result["status"]
        out_row["processing_error"] = result["error"] or ""
        
        info = result["company_info"]
        if info:
            # Serialize the full nested object to JSON
            out_row["enriched_data"] = info.model_dump_json()
            stats["success"] += 1
        else:
            out_row["enriched_data"] = ""
            stats["failed"] += 1
            
        enriched_results.append(out_row)

    # 5. Write Results
    save_csv(args.output, enriched_results, fieldnames)
    
    # 6. Summary
    logger.info("--- Processing Complete ---")
    logger.info(f"Total: {stats['processed']}")
    logger.info(f"Success: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Output written to: {args.output}")

if __name__ == "__main__":
    main()
