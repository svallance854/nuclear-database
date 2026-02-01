"""Script 1: Ingest NRC operating reactor data into sites and reactors tables.

Source: https://www.nrc.gov/reactors/operating/list-power-reactor-units.html
"""
import re
import requests
from bs4 import BeautifulSoup
from db_utils import get_connection, init_db, setup_logging

logger = setup_logging("ingest_nrc_reactors")

NRC_URL = "https://www.nrc.gov/reactors/operating/list-power-reactor-units.html"

# Map NRC reactor type strings to our schema values
REACTOR_TYPE_MAP = {
    "PWR": "PWR",
    "BWR": "BWR",
    "HTGR": "HTGR",
}

US_STATE_ABBREVS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}


def parse_docket(text: str) -> str | None:
    """Extract docket number like '05000xxx' from text."""
    m = re.search(r"0500\d{4}", text)
    return m.group(0) if m else None


def parse_unit_number(name: str) -> int | None:
    """Extract unit number from reactor name like 'Braidwood 1'."""
    m = re.search(r"(\d+)\s*$", name.strip())
    return int(m.group(1)) if m else None


def derive_site_name(reactor_name: str) -> str:
    """Derive site name by stripping trailing unit number."""
    return re.sub(r"\s*,?\s*(Unit\s*)?\d+\s*$", "", reactor_name).strip()


def fetch_and_parse():
    """Fetch NRC page and parse reactor table rows."""
    logger.info("Fetching NRC operating reactors page...")
    resp = requests.get(NRC_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table")
    if not table:
        logger.error("Could not find reactor table on NRC page")
        return []

    rows = table.find_all("tr")[1:]  # skip header
    reactors = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        try:
            # Column layout: Plant Name/Docket | License | Reactor Type | Location | Owner/Operator | Region
            name_text = cells[0].get_text(strip=True)
            # Docket is in parentheses like "Arkansas Nuclear 1 (05000313)"
            docket = parse_docket(name_text)
            # Also check link href
            link = cells[0].find("a")
            if not docket and link and link.get("href"):
                docket = parse_docket(link["href"])
            # Strip docket from name
            name = re.sub(r"\s*\(\d+\)\s*$", "", name_text).strip()

            reactor_type_raw = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            reactor_type = REACTOR_TYPE_MAP.get(reactor_type_raw, "Other")

            location = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            owner = cells[4].get_text(strip=True) if len(cells) > 4 else ""

            # Parse state from location (e.g. "6 miles WNW of Russellville, AR")
            state = ""
            state_match = re.search(r",\s*([A-Z]{2})\b", location)
            if state_match:
                state = state_match.group(1)
            else:
                for state_name, abbrev in US_STATE_ABBREVS.items():
                    if state_name in location:
                        state = abbrev
                        break

            reactors.append({
                "name": name,
                "site_name": derive_site_name(name),
                "unit_number": parse_unit_number(name),
                "docket": docket,
                "reactor_type": reactor_type,
                "capacity_mw": None,
                "location": location,
                "state": state or "Unknown",
                "owner": owner,
                "license_expiration_date": None,
            })
        except Exception as e:
            logger.warning("Error parsing row: %s — %s", row.get_text(strip=True)[:80], e)

    logger.info("Parsed %d reactor entries", len(reactors))
    return reactors


def upsert_reactors(reactors: list[dict]):
    """Insert or update sites and reactors in the database."""
    conn = get_connection()
    inserted_sites = 0
    inserted_reactors = 0
    updated_reactors = 0

    for r in reactors:
        # Upsert site
        existing_site = conn.execute(
            "SELECT id FROM sites WHERE name = ?", (r["site_name"],)
        ).fetchone()

        if existing_site:
            site_id = existing_site["id"]
        else:
            cur = conn.execute(
                """INSERT INTO sites (name, state, owner, operator, site_type, total_capacity_mw)
                   VALUES (?, ?, ?, ?, 'operating', ?)""",
                (r["site_name"], r["state"], r["owner"], r["owner"], r["capacity_mw"]),
            )
            site_id = cur.lastrowid
            inserted_sites += 1

        # Upsert reactor by docket number
        if r["docket"]:
            existing = conn.execute(
                "SELECT id FROM reactors WHERE nrc_docket_number = ?", (r["docket"],)
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE reactors SET name=?, reactor_type=?, capacity_mw=?,
                       license_expiration_date=?, status='operating'
                       WHERE nrc_docket_number=?""",
                    (r["name"], r["reactor_type"], r["capacity_mw"],
                     r["license_expiration_date"], r["docket"]),
                )
                updated_reactors += 1
            else:
                conn.execute(
                    """INSERT INTO reactors
                       (site_id, name, unit_number, reactor_type, capacity_mw,
                        license_expiration_date, nrc_docket_number, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'operating')""",
                    (site_id, r["name"], r["unit_number"], r["reactor_type"],
                     r["capacity_mw"], r["license_expiration_date"], r["docket"]),
                )
                inserted_reactors += 1
        else:
            # No docket — insert if name doesn't exist
            existing = conn.execute(
                "SELECT id FROM reactors WHERE name = ? AND site_id = ?",
                (r["name"], site_id),
            ).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO reactors
                       (site_id, name, unit_number, reactor_type, capacity_mw,
                        license_expiration_date, status)
                       VALUES (?, ?, ?, ?, ?, ?, 'operating')""",
                    (site_id, r["name"], r["unit_number"], r["reactor_type"],
                     r["capacity_mw"], r["license_expiration_date"]),
                )
                inserted_reactors += 1

    conn.commit()
    conn.close()
    logger.info(
        "Sites: %d new | Reactors: %d new, %d updated",
        inserted_sites, inserted_reactors, updated_reactors,
    )


def main():
    init_db()
    reactors = fetch_and_parse()
    if reactors:
        upsert_reactors(reactors)
    else:
        logger.warning("No reactors parsed — check if NRC page format changed")


if __name__ == "__main__":
    main()
