"""Ingest NRC ADAMS documents via the public ADAMS search API.

Source: https://adams.nrc.gov/wba/
Searches for recent documents by docket numbers already in the database.
"""
import re
import requests
from db_utils import get_connection, init_db, setup_logging

logger = setup_logging("ingest_adams")

ADAMS_SEARCH_URL = "https://adams.nrc.gov/wba/services/search/advanced/nrc"


def get_tracked_dockets() -> list[str]:
    """Get all docket numbers currently in the database."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT nrc_docket_number FROM reactors WHERE nrc_docket_number IS NOT NULL"
    ).fetchall()
    conn.close()
    return [r["nrc_docket_number"] for r in rows]


def search_adams(docket: str, max_results: int = 20) -> list[dict]:
    """Search ADAMS for documents related to a docket number."""
    # ADAMS uses a specific query format
    params = {
        "q": f'\"properties/DocketNumber:{docket}\"',
        "qn": "New",
        "tab": "content-search-pars",
        "s": "DocumentDate",
        "so": "DESC",
        "max_results": str(max_results),
    }
    try:
        resp = requests.get(ADAMS_SEARCH_URL, params=params, timeout=30,
                           headers={"Accept": "application/json", "User-Agent": "NuclearDB/1.0"})
        if resp.status_code != 200:
            logger.debug("ADAMS search returned %d for docket %s", resp.status_code, docket)
            return []

        data = resp.json()
        results = data if isinstance(data, list) else data.get("results", data.get("hits", []))
        docs = []
        for item in results:
            if isinstance(item, dict):
                props = item.get("properties", item)
                accession = props.get("AccessionNumber", props.get("accession_number", ""))
                title = props.get("DocumentTitle", props.get("title", ""))
                doc_date = props.get("DocumentDate", props.get("document_date", ""))
                doc_type = props.get("DocumentType", props.get("document_type", ""))
                if accession:
                    docs.append({
                        "accession_number": accession.strip(),
                        "title": (title or "Untitled").strip()[:500],
                        "document_date": doc_date,
                        "docket_number": docket,
                        "document_type": doc_type,
                        "adams_url": f"https://adams.nrc.gov/wba/services/search/getContent/{accession}",
                    })
        return docs
    except Exception as e:
        logger.warning("ADAMS search error for docket %s: %s", docket, e)
        return []


def store_documents(docs: list[dict]):
    """Insert ADAMS documents, skipping duplicates by accession number."""
    conn = get_connection()
    stored = 0
    skipped = 0

    for d in docs:
        existing = conn.execute(
            "SELECT id FROM adams_documents WHERE accession_number = ?",
            (d["accession_number"],),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        # Link to site/reactor via docket
        reactor = conn.execute(
            "SELECT id, site_id FROM reactors WHERE nrc_docket_number = ?",
            (d["docket_number"],),
        ).fetchone()
        site_id = reactor["site_id"] if reactor else None
        reactor_id = reactor["id"] if reactor else None

        conn.execute(
            """INSERT INTO adams_documents
               (accession_number, title, document_date, docket_number, document_type,
                site_id, reactor_id, adams_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (d["accession_number"], d["title"], d["document_date"], d["docket_number"],
             d["document_type"], site_id, reactor_id, d["adams_url"]),
        )
        stored += 1

    conn.commit()
    conn.close()
    logger.info("ADAMS docs: %d stored, %d skipped (duplicates)", stored, skipped)


def main():
    init_db()
    dockets = get_tracked_dockets()
    logger.info("Searching ADAMS for %d tracked docket numbers...", len(dockets))

    all_docs = []
    for docket in dockets:
        docs = search_adams(docket, max_results=10)
        all_docs.extend(docs)

    logger.info("Found %d total documents", len(all_docs))
    if all_docs:
        store_documents(all_docs)


if __name__ == "__main__":
    main()
