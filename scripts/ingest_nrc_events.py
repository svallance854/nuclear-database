"""Script 5: Ingest NRC press releases and event reports.

Source: NRC RSS feeds and press release pages.
URL: https://www.nrc.gov/reading-rm/doc-collections/news/
Objective: Capture regulatory events and market-moving news.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from db_utils import get_connection, init_db, setup_logging

logger = setup_logging("ingest_nrc_events")

# NRC RSS feeds
NRC_RSS_FEEDS = [
    "https://www.nrc.gov/reading-rm/doc-collections/news/rss-nrc-news.xml",
]

# Fallback: scrape the news page
NRC_NEWS_URL = "https://www.nrc.gov/reading-rm/doc-collections/news/"

# Keywords for categorizing events
EVENT_TYPE_KEYWORDS = {
    "license-renewal": ["license renewal", "renewed", "slr", "subsequent license"],
    "license-amendment": ["license amendment", "amendment"],
    "inspection": ["inspection", "inspector", "inspected"],
    "enforcement": ["enforcement", "violation", "penalty", "fine", "civil penalty"],
    "exemption": ["exemption", "exempt"],
    "rulemaking": ["rulemaking", "rule", "proposed rule", "final rule"],
    "hearing": ["hearing", "adjudicatory"],
}


def classify_event(text: str) -> str:
    """Classify an event based on keyword matching."""
    text_lower = text.lower()
    for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return event_type
    return "other"


def extract_docket(text: str) -> str | None:
    """Extract a docket number from text."""
    m = re.search(r"(?:docket|0500)\s*(?:no\.?\s*)?(\d{4,8})", text, re.IGNORECASE)
    if m:
        num = m.group(1)
        if len(num) <= 4:
            return f"0500{num.zfill(4)}"
        return num
    return None


def parse_rss_feed(url: str) -> list[dict]:
    """Parse an NRC RSS feed for news items."""
    logger.info("Fetching RSS feed: %s", url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        items = []
        # Handle both RSS 2.0 and Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            description = item.findtext("description", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()

            if not title:
                continue

            # Parse date
            event_date = None
            if pub_date:
                for fmt in [
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%a, %d %b %Y %H:%M:%S GMT",
                    "%Y-%m-%dT%H:%M:%S%z",
                ]:
                    try:
                        dt = datetime.strptime(pub_date, fmt)
                        event_date = dt.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue

            full_text = f"{title} {description}"
            items.append({
                "title": title,
                "description": description,
                "source_url": link,
                "event_date": event_date,
                "event_type": classify_event(full_text),
                "docket": extract_docket(full_text),
            })

        logger.info("Parsed %d items from RSS", len(items))
        return items
    except Exception as e:
        logger.error("Failed to parse RSS feed: %s", e)
        return []


def scrape_news_page() -> list[dict]:
    """Fallback: scrape NRC news releases for the current year."""
    from datetime import date
    year = date.today().year
    year_url = f"https://www.nrc.gov/reading-rm/doc-collections/news/{year}/"
    logger.info("Scraping NRC news page: %s", year_url)
    try:
        resp = requests.get(year_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            if not text or len(text) < 20:
                continue
            # Press release links typically contain the year and end with .html
            if href.endswith(".html") or href.endswith(".htm"):
                if not href.startswith("http"):
                    href = "https://www.nrc.gov" + href
                # Extract date from link text if present (e.g. "January 15, 2026")
                event_date = None
                date_match = re.search(
                    r"(\w+ \d{1,2},?\s*\d{4})", text
                )
                if date_match:
                    for fmt in ["%B %d, %Y", "%B %d %Y"]:
                        try:
                            dt = datetime.strptime(date_match.group(1), fmt)
                            event_date = dt.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue

                full_text = text
                items.append({
                    "title": text[:500],
                    "description": "",
                    "source_url": href,
                    "event_date": event_date,
                    "event_type": classify_event(full_text),
                    "docket": extract_docket(full_text),
                })

        logger.info("Scraped %d items from news page", len(items))
        return items
    except Exception as e:
        logger.error("Failed to scrape news page: %s", e)
        return []


def link_to_site(conn, docket: str | None) -> tuple[int | None, int | None]:
    """Try to link an event to a site/reactor via docket number."""
    if not docket:
        return None, None
    reactor = conn.execute(
        "SELECT id, site_id FROM reactors WHERE nrc_docket_number = ?", (docket,)
    ).fetchone()
    if reactor:
        return reactor["site_id"], reactor["id"]
    return None, None


def store_events(items: list[dict]):
    """Store parsed events into regulatory_events table."""
    conn = get_connection()
    stored = 0
    skipped = 0

    for item in items:
        # Deduplicate by title
        existing = conn.execute(
            "SELECT id FROM regulatory_events WHERE title = ?", (item["title"],)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        site_id, reactor_id = link_to_site(conn, item["docket"])

        # Extract NRC document ID from URL if possible
        nrc_doc_id = None
        if item["source_url"]:
            m = re.search(r"(ML\d{8,}|\d{4}-\d{3,})", item["source_url"])
            if m:
                nrc_doc_id = m.group(1)

        conn.execute(
            """INSERT INTO regulatory_events
               (site_id, reactor_id, event_type, title, description,
                event_date, nrc_document_id, source_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                site_id,
                reactor_id,
                item["event_type"],
                item["title"],
                item["description"],
                item["event_date"],
                nrc_doc_id,
                item["source_url"],
            ),
        )
        stored += 1

    conn.commit()
    conn.close()
    logger.info("Regulatory events: %d stored, %d skipped (duplicates)", stored, skipped)


def main():
    init_db()

    # Try RSS feeds first
    all_items = []
    for feed_url in NRC_RSS_FEEDS:
        all_items.extend(parse_rss_feed(feed_url))

    # Fallback to scraping if RSS returned nothing
    if not all_items:
        logger.info("RSS feeds empty, falling back to page scrape")
        all_items = scrape_news_page()

    if all_items:
        store_events(all_items)
    else:
        logger.warning("No events found from any source")


if __name__ == "__main__":
    main()
