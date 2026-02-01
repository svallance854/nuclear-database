"""Ingest uranium and SWU spot prices.

Scrapes publicly available uranium price data from Cameco's investor page
or similar public sources. For production use with UxC/TradeTech, add API
credentials to settings.
"""
import re
import requests
from bs4 import BeautifulSoup
from db_utils import get_connection, init_db, setup_logging

logger = setup_logging("ingest_uranium_prices")

# Public uranium price sources (best-effort scraping)
CAMECO_URL = "https://www.cameco.com/invest/markets/uranium-price"


def fetch_cameco_prices() -> list[dict]:
    """Scrape uranium spot price from Cameco's public page."""
    logger.info("Fetching uranium prices from Cameco...")
    try:
        resp = requests.get(CAMECO_URL, timeout=30, headers={"User-Agent": "NuclearDB/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        prices = []
        # Look for price data in page text
        text = soup.get_text()

        # Try to find U3O8 spot price pattern like "$XX.XX"
        # Cameco typically shows "Uranium spot price US$ XX.XX /lb U3O8"
        matches = re.findall(
            r"(?:spot|price)[^$]*\$\s*([\d,.]+)\s*/?\s*lb",
            text, re.IGNORECASE,
        )
        for m in matches:
            try:
                price = float(m.replace(",", ""))
                if 10 < price < 500:  # sanity check for uranium price range
                    prices.append({
                        "commodity": "U3O8",
                        "price": price,
                        "unit": "lb",
                        "source": "Cameco",
                        "source_url": CAMECO_URL,
                    })
                    break
            except ValueError:
                continue

        # Try to find SWU price
        swu_matches = re.findall(
            r"SWU[^$]*\$\s*([\d,.]+)",
            text, re.IGNORECASE,
        )
        for m in swu_matches:
            try:
                price = float(m.replace(",", ""))
                if 50 < price < 500:
                    prices.append({
                        "commodity": "SWU",
                        "price": price,
                        "unit": "SWU",
                        "source": "Cameco",
                        "source_url": CAMECO_URL,
                    })
                    break
            except ValueError:
                continue

        logger.info("Parsed %d price entries", len(prices))
        return prices
    except requests.RequestException as e:
        logger.error("Failed to fetch Cameco page: %s", e)
        return []


def store_prices(prices: list[dict]):
    """Insert new price records, skip if same commodity+date already exists."""
    conn = get_connection()
    stored = 0
    from datetime import date
    today = date.today().isoformat()

    for p in prices:
        existing = conn.execute(
            "SELECT id FROM commodity_prices WHERE commodity = ? AND price_date = ?",
            (p["commodity"], today),
        ).fetchone()
        if existing:
            logger.debug("Price for %s on %s already exists, skipping", p["commodity"], today)
            continue
        conn.execute(
            """INSERT INTO commodity_prices (commodity, price, unit, price_date, source, source_url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (p["commodity"], p["price"], p["unit"], today, p["source"], p["source_url"]),
        )
        stored += 1

    conn.commit()
    conn.close()
    logger.info("Stored %d new price records", stored)


def main():
    init_db()
    prices = fetch_cameco_prices()
    if prices:
        store_prices(prices)
    else:
        logger.warning("No prices parsed — source format may have changed")


if __name__ == "__main__":
    main()
