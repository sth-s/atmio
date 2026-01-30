#!/usr/bin/env python3
"""Company Research Agent - CLI entry point."""

import argparse
import csv
import sys
import time
from agent.graph import build_agent


def load_all_companies(csv_path: str = "data/companies.csv") -> list[dict]:
    """Load all companies from CSV."""
    companies = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append({
                    'company_name': row.get('Unternehmensname', ''),
                    'domain': row.get('Domainname des Unternehmens', ''),
                    'city': row.get('Stadt', ''),
                    'address': row.get('Adresszeile', ''),
                    'industry': row.get('Branche', ''),
                })
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    return companies


def load_company_from_csv(company_name: str, csv_path: str = "data/companies.csv") -> dict | None:
    """Load company data from CSV by name."""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if company_name.lower() in row.get('Unternehmensname', '').lower():
                    return {
                        'company_name': row.get('Unternehmensname', ''),
                        'domain': row.get('Domainname des Unternehmens', ''),
                        'city': row.get('Stadt', ''),
                        'address': row.get('Adresszeile', ''),
                        'industry': row.get('Branche', ''),
                    }
    except FileNotFoundError:
        pass
    return None


def research_company(agent, company_data: dict) -> dict | None:
    """Research a single company and return the result."""
    company_name = company_data['company_name']
    domain = company_data.get('domain', '')

    initial_state = {
        'company_name': company_name,
        'domain': domain,
        'company_profile': {
            'location': company_data.get('city', ''),
            'address': company_data.get('address', ''),
            'industry': company_data.get('industry', ''),
        },
        'errors': [],
    }

    try:
        result = agent.invoke(initial_state)
        return result
    except Exception as e:
        print(f"  Error: {e}")
        return None


def run_batch(csv_path: str, limit: int = None, delay: float = 2.0):
    """Process all companies from CSV."""
    companies = load_all_companies(csv_path)

    if limit:
        companies = companies[:limit]

    total = len(companies)
    print(f"Processing {total} companies from {csv_path}")
    print("=" * 60)

    agent = build_agent()

    successful = 0
    failed = 0
    with_contact = 0

    for i, company_data in enumerate(companies, 1):
        company_name = company_data['company_name']
        domain = company_data.get('domain', '')

        print(f"\n[{i}/{total}] {company_name}")
        print(f"  Domain: {domain or 'N/A'}")

        result = research_company(agent, company_data)

        if result:
            successful += 1
            if result.get('contact', {}).get('email') or result.get('contact', {}).get('phone'):
                with_contact += 1
                contact = result['contact']
                print(f"  Contact: {contact.get('email') or contact.get('phone')}")
            else:
                print(f"  No contact found")

            if result.get('report_path'):
                print(f"  Saved: {result['report_path']}")
        else:
            failed += 1
            print(f"  FAILED")

        # Delay between requests to be polite to servers
        if i < total:
            time.sleep(delay)

    # Summary
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    print(f"Total:        {total}")
    print(f"Successful:   {successful}")
    print(f"With contact: {with_contact}")
    print(f"Failed:       {failed}")


def run_single(company_name: str, domain: str, csv_path: str):
    """Process a single company."""
    csv_data = load_company_from_csv(company_name, csv_path)

    if csv_data:
        print(f"Found in CSV: {csv_data['company_name']}")
        company_data = csv_data
        if domain:
            company_data['domain'] = domain
    else:
        print(f"Company not found in CSV, using provided name: {company_name}")
        company_data = {
            'company_name': company_name,
            'domain': domain,
            'city': '',
            'address': '',
            'industry': '',
        }

    if not company_data.get('domain'):
        print("Warning: No domain provided. Website scraping will be skipped.")

    print(f"\nResearching: {company_data['company_name']}")
    print(f"Domain: {company_data.get('domain') or 'N/A'}")
    print("-" * 40)

    agent = build_agent()
    result = research_company(agent, company_data)

    print("\n" + "=" * 40)
    print("RESEARCH COMPLETE")
    print("=" * 40)

    if result:
        if result.get('contact'):
            contact = result['contact']
            print(f"\nContact found:")
            print(f"  Name:  {contact.get('name') or 'N/A'}")
            print(f"  Role:  {contact.get('role') or 'N/A'}")
            print(f"  Email: {contact.get('email') or 'N/A'}")
            print(f"  Phone: {contact.get('phone') or 'N/A'}")
        else:
            print("\nNo contact found.")

        if result.get('report_path'):
            print(f"\nReport saved to: {result['report_path']}")
    else:
        print("\nResearch failed.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Research Italian companies and generate sales reports."
    )
    parser.add_argument(
        "company_name",
        nargs="?",
        help="Name of the company to research (omit for batch mode)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all companies from CSV"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of companies to process in batch mode"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between companies (default: 2.0)"
    )
    parser.add_argument(
        "--domain",
        help="Company domain (optional if company is in CSV)",
        default=""
    )
    parser.add_argument(
        "--csv",
        help="Path to companies CSV file",
        default="data/companies.csv"
    )

    args = parser.parse_args()

    if args.batch:
        run_batch(args.csv, args.limit, args.delay)
    elif args.company_name:
        run_single(args.company_name, args.domain, args.csv)
    else:
        # Default: batch mode
        run_batch(args.csv, args.limit, args.delay)


if __name__ == "__main__":
    main()
