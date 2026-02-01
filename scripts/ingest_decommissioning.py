"""Script 2: Ingest NRC decommissioning sites.

Source: https://www.nrc.gov/info-finder/decommissioning/power-reactor/
"""
import re
import requests
from bs4 import BeautifulSoup
from db_utils import get_connection, init_db, setup_logging

logger = setup_logging("ingest_decommissioning")

NRC_DECOM_URL = "https://www.nrc.gov/info-finder/decommissioning/power-reactor/"

# Map NRC decommissioning status strings to our schema
STATUS_MAP = {
    "safstor": "decommissioning",
    "decon": "decommissioning",
    "license terminated": "decommissioned",
    "terminated": "decommissioned",
    "dismantling": "decommissioning",
    "operating": "operating",
}

SITE_TYPE_MAP = {
    "safstor": "decommissioning",
    "decon": "decommissioning",
    "license terminated": "decommissioned",
    "terminated": "decommissioned",
    "dismantling": "decommissioning",
}


def parse_docket(text: str) -> str | None:
    m = re.search(r"0500\d{4}", text)
    return m.group(0) if m else None


def fetch_and_parse():
    """Fetch NRC decommissioning page and parse reactor list."""
    logger.info("Fetching NRC decommissioning page...")
    resp = requests.get(NRC_DECOM_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    # The data table has 8-column header row; skip layout tables
    table = None
    for t in tables:
        first_row = t.find("tr")
        if first_row and len(first_row.find_all(["th", "td"])) >= 8:
            table = t
            break
    if not table:
        logger.error("Could not find decommissioning table on NRC page")
        return []

    rows = table.find_all("tr")[1:]
    entries = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        try:
            # Column layout: Name | Acronym | Docket | License | ISFSI | PM | Location | License Status
            name = cells[0].get_text(strip=True)
            link = cells[0].find("a")

            # Docket is in column 2 (index 2)
            docket_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            docket = parse_docket(docket_text)
            if not docket and link and link.get("href"):
                docket = parse_docket(link["href"])

            # Location is column 6
            location = cells[6].get_text(strip=True) if len(cells) > 6 else ""
            # License Status is column 7 (SAFSTOR, DECON, etc.)
            status_raw = cells[7].get_text(strip=True).lower() if len(cells) > 7 else ""

            # Extract state from location (e.g. "Middletown, PA")
            state = "Unknown"
            state_match = re.search(r",\s*([A-Z]{2})\b", location)
            if state_match:
                state = state_match.group(1)

            # Map status
            reactor_status = "permanently-shutdown"
            site_type = "decommissioning"
            for key, val in STATUS_MAP.items():
                if key in status_raw:
                    reactor_status = "decommissioning" if val == "decommissioning" else "decommissioned"
                    break
            for key, val in SITE_TYPE_MAP.items():
                if key in status_raw:
                    site_type = val
                    break

            entries.append({
                "name": name,
                "site_name": re.sub(r"\s*[-–]\s*(Unit\s*)?\d+\s*$", "", name).strip(),
                "docket": docket,
                "location": location,
                "state": state,
                "status_raw": status_raw,
                "reactor_status": reactor_status,
                "site_type": site_type,
                "reactor_type": "Other",
            })
        except Exception as e:
            logger.warning("Error parsing row: %s — %s", row.get_text(strip=True)[:80], e)

    logger.info("Parsed %d decommissioning entries", len(entries))
    return entries


def upsert_decommissioning(entries: list[dict]):
    """Insert or update decommissioning sites and reactors."""
    conn = get_connection()
    new_sites = 0
    new_reactors = 0
    updated = 0

    for e in entries:
        # Find or create site
        existing_site = conn.execute(
            "SELECT id FROM sites WHERE name = ?", (e["site_name"],)
        ).fetchone()

        if existing_site:
            site_id = existing_site["id"]
            conn.execute(
                "UPDATE sites SET site_type = ? WHERE id = ?",
                (e["site_type"], site_id),
            )
        else:
            cur = conn.execute(
                """INSERT INTO sites (name, state, site_type)
                   VALUES (?, ?, ?)""",
                (e["site_name"], e["state"], e["site_type"]),
            )
            site_id = cur.lastrowid
            new_sites += 1

        # Upsert reactor
        if e["docket"]:
            existing = conn.execute(
                "SELECT id FROM reactors WHERE nrc_docket_number = ?", (e["docket"],)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE reactors SET status = ? WHERE nrc_docket_number = ?",
                    (e["reactor_status"], e["docket"]),
                )
                updated += 1
            else:
                conn.execute(
                    """INSERT INTO reactors (site_id, name, nrc_docket_number, reactor_type, status)
                       VALUES (?, ?, ?, ?, ?)""",
                    (site_id, e["name"], e["docket"], e["reactor_type"], e["reactor_status"]),
                )
                new_reactors += 1
        else:
            existing = conn.execute(
                "SELECT id FROM reactors WHERE name = ? AND site_id = ?",
                (e["name"], site_id),
            ).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO reactors (site_id, name, reactor_type, status)
                       VALUES (?, ?, ?, ?)""",
                    (site_id, e["name"], e["reactor_type"], e["reactor_status"]),
                )
                new_reactors += 1

    conn.commit()
    conn.close()
    logger.info("Sites: %d new | Reactors: %d new, %d updated", new_sites, new_reactors, updated)


def main():
    init_db()
    entries = fetch_and_parse()
    if entries:
        upsert_decommissioning(entries)
    else:
        logger.warning("No entries parsed — check if NRC page format changed")


if __name__ == "__main__":
    main()
