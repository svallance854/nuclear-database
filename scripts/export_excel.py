"""Export database tables to Excel workbook for deal memos and reporting.

Usage:
    python scripts/export_excel.py                        # export all tables
    python scripts/export_excel.py --tables sites reactors # export specific tables
    python scripts/export_excel.py --output report.xlsx    # custom output path
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATABASE_PATH
from db_utils import init_db, setup_logging
import sqlite3

logger = setup_logging("export_excel")

EXPORTABLE_TABLES = {
    "sites": "SELECT * FROM sites ORDER BY name",
    "reactors": """
        SELECT r.*, s.name as site_name
        FROM reactors r JOIN sites s ON r.site_id = s.id
        ORDER BY s.name, r.unit_number
    """,
    "companies": "SELECT * FROM companies ORDER BY name",
    "contracts": """
        SELECT ct.*, c.name as company_name, s.name as site_name
        FROM contracts ct
        JOIN companies c ON ct.company_id = c.id
        JOIN sites s ON ct.site_id = s.id
        ORDER BY ct.start_date DESC
    """,
    "decommissioning_trust_funds": """
        SELECT d.*, s.name as site_name
        FROM decommissioning_trust_funds d
        JOIN sites s ON d.site_id = s.id
        ORDER BY s.name
    """,
    "regulatory_events": "SELECT * FROM regulatory_events ORDER BY event_date DESC",
    "market_events": "SELECT * FROM market_events ORDER BY event_date DESC",
    "smr_projects": """
        SELECT p.*, c.name as developer_name
        FROM smr_projects p
        LEFT JOIN companies c ON p.developer_id = c.id
        ORDER BY p.name
    """,
    "deals": """
        SELECT d.*, c.name as company_name, s.name as site_name
        FROM deals d
        LEFT JOIN companies c ON d.company_id = c.id
        LEFT JOIN sites s ON d.site_id = s.id
        ORDER BY d.stage, d.title
    """,
    "commodity_prices": "SELECT * FROM commodity_prices ORDER BY price_date DESC",
    "company_financials": """
        SELECT f.*, c.name as company_name
        FROM company_financials f
        JOIN companies c ON f.company_id = c.id
        ORDER BY c.name, f.fiscal_year DESC, f.fiscal_quarter DESC
    """,
}


def export(tables: list[str] | None = None, output: str = "nuclear_export.xlsx"):
    """Export selected tables to an Excel workbook."""
    init_db()
    conn = sqlite3.connect(DATABASE_PATH)

    # Determine which tables exist
    existing = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    selected = tables or list(EXPORTABLE_TABLES.keys())
    output_path = Path(output)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        sheets_written = 0
        for table in selected:
            if table not in EXPORTABLE_TABLES:
                logger.warning("Unknown table: %s, skipping", table)
                continue
            # Check the base table exists
            base_table = table.split()[0]
            if base_table not in existing:
                logger.debug("Table %s doesn't exist yet, skipping", base_table)
                continue

            try:
                df = pd.read_sql_query(EXPORTABLE_TABLES[table], conn)
                # Truncate sheet name to Excel 31-char limit
                sheet_name = table[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                sheets_written += 1
                logger.info("Exported %s: %d rows", table, len(df))
            except Exception as e:
                logger.warning("Failed to export %s: %s", table, e)

    conn.close()

    if sheets_written > 0:
        logger.info("Workbook saved to %s (%d sheets)", output_path.resolve(), sheets_written)
    else:
        logger.warning("No data exported")
        output_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Export nuclear DB to Excel")
    parser.add_argument("--tables", nargs="*", help="Tables to export (default: all)")
    parser.add_argument("--output", default="nuclear_export.xlsx", help="Output file path")
    args = parser.parse_args()
    export(tables=args.tables, output=args.output)


if __name__ == "__main__":
    main()
