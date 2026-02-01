"""Script 4: Ingest NRC Decommissioning Trust Fund data.

Source: NRC annual decommissioning funding status reports (PDF/HTML).
Objective: Populate decommissioning_trust_funds table.
"""
import re
import requests
from bs4 import BeautifulSoup
from db_utils import get_connection, init_db, setup_logging

logger = setup_logging("ingest_trust_funds")

# NRC publishes annual decommissioning funding reports
NRC_DECOM_FUNDING_URL = (
    "https://www.nrc.gov/waste/decommissioning/finan-assur/decom-fnd-status-rpts.html"
)


def find_latest_report_url() -> str | None:
    """Scrape the NRC page to find the latest funding status report link."""
    logger.info("Looking for latest decommissioning funding report...")
    try:
        resp = requests.get(NRC_DECOM_FUNDING_URL, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for PDF or HTML links to annual reports
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True).lower()
            if ("report" in text or "status" in text) and (
                href.endswith(".pdf") or href.endswith(".html") or href.endswith(".htm")
            ):
                if not href.startswith("http"):
                    href = "https://www.nrc.gov" + href
                logger.info("Found report: %s", href)
                return href
    except requests.RequestException as e:
        logger.error("Failed to fetch NRC funding reports page: %s", e)
    return None


def parse_funding_table_from_html(url: str) -> list[dict]:
    """Try to parse a funding report if it's in HTML table format."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        table = soup.find("table")
        if not table:
            logger.warning("No table found in report at %s", url)
            return []

        rows = table.find_all("tr")[1:]
        entries = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            try:
                plant_name = cells[0].get_text(strip=True)
                fund_text = cells[1].get_text(strip=True).replace(",", "").replace("$", "")
                cost_text = cells[2].get_text(strip=True).replace(",", "").replace("$", "")

                fund_balance = None
                estimated_cost = None
                fund_match = re.search(r"[\d.]+", fund_text)
                cost_match = re.search(r"[\d.]+", cost_text)
                if fund_match:
                    fund_balance = float(fund_match.group(0))
                if cost_match:
                    estimated_cost = float(cost_match.group(0))

                entries.append({
                    "plant_name": plant_name,
                    "fund_balance": fund_balance,
                    "estimated_cost": estimated_cost,
                    "source_url": url,
                })
            except Exception as e:
                logger.warning("Error parsing funding row: %s", e)
        return entries
    except requests.RequestException as e:
        logger.error("Failed to fetch report: %s", e)
        return []


def parse_funding_from_pdf(url: str) -> list[dict]:
    """Parse funding data from a PDF report using pdfplumber."""
    try:
        import pdfplumber
        import tempfile
    except ImportError:
        logger.error("pdfplumber not installed — cannot parse PDF reports")
        return []

    try:
        logger.info("Downloading PDF: %s", url)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()

        entries = []
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 3:
                            continue
                        plant_name = (row[0] or "").strip()
                        if not plant_name or plant_name.lower() in ("plant", "facility", "name"):
                            continue

                        fund_text = (row[1] or "").replace(",", "").replace("$", "")
                        cost_text = (row[2] or "").replace(",", "").replace("$", "")

                        fund_balance = None
                        estimated_cost = None
                        fm = re.search(r"[\d.]+", fund_text)
                        cm = re.search(r"[\d.]+", cost_text)
                        if fm:
                            fund_balance = float(fm.group(0))
                        if cm:
                            estimated_cost = float(cm.group(0))

                        entries.append({
                            "plant_name": plant_name,
                            "fund_balance": fund_balance,
                            "estimated_cost": estimated_cost,
                            "source_url": url,
                        })

        import os
        os.unlink(tmp_path)
        return entries
    except Exception as e:
        logger.error("Failed to parse PDF: %s", e)
        return []


def upsert_trust_funds(entries: list[dict]):
    """Insert or update trust fund records."""
    conn = get_connection()
    stored = 0
    skipped = 0

    for e in entries:
        # Find matching site
        site = conn.execute(
            "SELECT id FROM sites WHERE name = ? OR name LIKE ?",
            (e["plant_name"], f"%{e['plant_name']}%"),
        ).fetchone()

        if not site:
            logger.debug("No site match for '%s', creating one", e["plant_name"])
            cur = conn.execute(
                "INSERT INTO sites (name, state, site_type) VALUES (?, 'Unknown', 'decommissioning')",
                (e["plant_name"],),
            )
            site_id = cur.lastrowid
        else:
            site_id = site["id"]

        # Check for existing record for this site
        existing = conn.execute(
            "SELECT id FROM decommissioning_trust_funds WHERE site_id = ?",
            (site_id,),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE decommissioning_trust_funds
                   SET fund_balance = ?, estimated_cost = ?, source_url = ?,
                       report_date = date('now')
                   WHERE id = ?""",
                (e["fund_balance"], e["estimated_cost"], e["source_url"], existing["id"]),
            )
            stored += 1
        else:
            conn.execute(
                """INSERT INTO decommissioning_trust_funds
                   (site_id, fund_balance, estimated_cost, report_date, source, source_url)
                   VALUES (?, ?, ?, date('now'), 'NRC Decommissioning Funding Report', ?)""",
                (site_id, e["fund_balance"], e["estimated_cost"], e["source_url"]),
            )
            stored += 1

    conn.commit()
    conn.close()
    logger.info("Trust funds: %d upserted, %d skipped", stored, skipped)


def main():
    init_db()

    report_url = find_latest_report_url()
    if not report_url:
        logger.warning("Could not find latest funding report URL")
        return

    if report_url.endswith(".pdf"):
        entries = parse_funding_from_pdf(report_url)
    else:
        entries = parse_funding_table_from_html(report_url)

    if entries:
        upsert_trust_funds(entries)
    else:
        logger.warning("No trust fund entries parsed from report")


if __name__ == "__main__":
    main()
