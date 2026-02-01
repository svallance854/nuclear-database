"""Diff detector — snapshots reactor/site state before ingestion, then detects changes after.

Usage:
    snapshot = take_snapshot()
    # ... run ingestion ...
    changes = detect_changes(snapshot, run_id)
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATABASE_PATH
from run_logger import log_change

# Fields we track for change detection
WATCHED_FIELDS = {
    "reactors": {
        "table": "reactors",
        "key": "id",
        "fields": ["status", "license_expiration_date", "capacity_mw", "permanent_shutdown_date"],
        "entity_type": "reactor",
    },
    "sites": {
        "table": "sites",
        "key": "id",
        "fields": ["site_type", "owner", "operator", "total_capacity_mw"],
        "entity_type": "site",
    },
}


def _get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def take_snapshot() -> dict[str, dict[int, dict]]:
    """Capture current state of watched fields. Returns {table: {id: {field: value}}}."""
    conn = _get_conn()
    snapshot = {}
    for name, cfg in WATCHED_FIELDS.items():
        cols = ", ".join([cfg["key"]] + cfg["fields"])
        rows = conn.execute(f"SELECT {cols} FROM {cfg['table']}").fetchall()
        snapshot[name] = {}
        for row in rows:
            row_dict = dict(row)
            entity_id = row_dict.pop(cfg["key"])
            snapshot[name][entity_id] = row_dict
    conn.close()
    return snapshot


def detect_changes(before: dict[str, dict[int, dict]], run_id: int) -> list[dict]:
    """Compare current state against a previous snapshot. Logs and returns changes."""
    conn = _get_conn()
    changes = []

    for name, cfg in WATCHED_FIELDS.items():
        cols = ", ".join([cfg["key"]] + cfg["fields"])
        rows = conn.execute(f"SELECT {cols} FROM {cfg['table']}").fetchall()

        for row in rows:
            row_dict = dict(row)
            entity_id = row_dict.pop(cfg["key"])
            old = before.get(name, {}).get(entity_id)
            if old is None:
                # New record — not a "change" we alert on
                continue
            for field in cfg["fields"]:
                old_val = str(old.get(field)) if old.get(field) is not None else None
                new_val = str(row_dict.get(field)) if row_dict.get(field) is not None else None
                if old_val != new_val:
                    change = {
                        "entity_type": cfg["entity_type"],
                        "entity_id": entity_id,
                        "field": field,
                        "old": old_val,
                        "new": new_val,
                    }
                    changes.append(change)
                    log_change(run_id, cfg["entity_type"], entity_id, field, old_val, new_val)

    conn.close()
    return changes
