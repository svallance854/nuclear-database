"""Script 3: Ingest nuclear-related government contracts from USAspending.gov API.

Source: https://api.usaspending.gov/api/v2
Objective: Identify nuclear service contractors with federal contracts.
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import USASPENDING_API_BASE, NUCLEAR_NAICS_CODES, NUCLEAR_AGENCIES
from db_utils import get_connection, init_db, setup_logging

logger = setup_logging("ingest_usaspending")

SEARCH_ENDPOINT = f"{USASPENDING_API_BASE}/search/spending_by_award/"


def fetch_contracts(naics_code: str, page: int = 1, limit: int = 100) -> list[dict]:
    """Query USAspending API for contracts by NAICS code."""
    payload = {
        "filters": {
            "naics_codes": [naics_code],
            "award_type_codes": ["A", "B", "C", "D"],  # contract types
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Start Date",
            "End Date",
            "Description",
            "Awarding Agency",
            "Awarding Sub Agency",
        ],
        "page": page,
        "limit": limit,
        "sort": "Award Amount",
        "order": "desc",
    }
    try:
        resp = requests.post(SEARCH_ENDPOINT, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.RequestException as e:
        logger.error("USAspending API error for NAICS %s: %s", naics_code, e)
        return []


AGENCY_KEYWORDS = ["ENERGY", "NUCLEAR", "DEFENSE", "ARMY", "NAVY"]


def is_nuclear_agency(agency: str) -> bool:
    """Check if the awarding agency is relevant (DOE, NRC, DOD)."""
    if not agency:
        return False
    agency_upper = agency.upper()
    return any(kw in agency_upper for kw in AGENCY_KEYWORDS)


def find_or_create_company(conn, name: str) -> int:
    """Find existing company by name or create a new one."""
    row = conn.execute(
        "SELECT id FROM companies WHERE name = ?", (name,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        """INSERT INTO companies (name, company_type) VALUES (?, 'contractor')""",
        (name,),
    )
    return cur.lastrowid


def ingest_contracts():
    """Fetch and store nuclear-related government contracts."""
    conn = get_connection()
    total_stored = 0
    total_skipped = 0

    for naics in NUCLEAR_NAICS_CODES:
        logger.info("Querying NAICS %s...", naics)
        results = fetch_contracts(naics)
        logger.info("  Got %d results for NAICS %s", len(results), naics)

        for award in results:
            agency = award.get("Awarding Agency", "") or ""
            sub_agency = award.get("Awarding Sub Agency", "") or ""

            # Filter to nuclear-relevant agencies
            if not (is_nuclear_agency(agency) or is_nuclear_agency(sub_agency)):
                total_skipped += 1
                continue

            recipient = award.get("Recipient Name", "").strip()
            if not recipient:
                continue

            award_id = award.get("Award ID", "")
            amount = award.get("Award Amount")
            start_date = award.get("Start Date")
            end_date = award.get("End Date")
            description = award.get("Description", "")

            # Check for duplicate by title (award ID)
            title = f"USAspending: {award_id} — {recipient}"
            existing = conn.execute(
                "SELECT id FROM market_events WHERE title = ?", (title,)
            ).fetchone()
            if existing:
                total_skipped += 1
                continue

            company_id = find_or_create_company(conn, recipient)

            conn.execute(
                """INSERT INTO market_events
                   (title, event_type, description, event_date, company_id,
                    financial_value, source_url)
                   VALUES (?, 'other', ?, ?, ?, ?, ?)""",
                (
                    title,
                    f"NAICS {naics} | Agency: {agency} / {sub_agency}\n{description}",
                    start_date,
                    company_id,
                    amount,
                    f"https://www.usaspending.gov/award/{award_id}" if award_id else None,
                ),
            )
            total_stored += 1

    conn.commit()
    conn.close()
    logger.info("Stored %d contract awards, skipped %d", total_stored, total_skipped)


def main():
    init_db()
    ingest_contracts()


if __name__ == "__main__":
    main()
