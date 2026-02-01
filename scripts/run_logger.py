"""Run logger — tracks script execution status and results."""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATABASE_PATH


def _get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    """Apply the run_logs migration if tables don't exist."""
    conn = _get_conn()
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='run_logs'"
    ).fetchone()
    if not existing:
        migration = Path(__file__).resolve().parent.parent / "database" / "migrations" / "001_run_logs_and_changes.sql"
        with open(migration) as f:
            conn.executescript(f.read())
    conn.close()


def start_run(script_name: str) -> int:
    """Log the start of a script run. Returns the run_log id."""
    ensure_tables()
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO run_logs (script_name, status) VALUES (?, 'started')",
        (script_name,),
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def finish_run(run_id: int, processed: int = 0, inserted: int = 0, updated: int = 0):
    """Log a successful run completion."""
    conn = _get_conn()
    conn.execute(
        """UPDATE run_logs SET status='success', finished_at=?,
           records_processed=?, records_inserted=?, records_updated=?
           WHERE id=?""",
        (datetime.now(timezone.utc).isoformat(), processed, inserted, updated, run_id),
    )
    conn.commit()
    conn.close()


def fail_run(run_id: int, error_message: str):
    """Log a failed run."""
    conn = _get_conn()
    conn.execute(
        "UPDATE run_logs SET status='failure', finished_at=?, error_message=? WHERE id=?",
        (datetime.now(timezone.utc).isoformat(), error_message, run_id),
    )
    conn.commit()
    conn.close()


def log_change(run_id: int, entity_type: str, entity_id: int,
               field_name: str, old_value: str | None, new_value: str | None):
    """Record a detected data change."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO data_changes (run_log_id, entity_type, entity_id,
           field_name, old_value, new_value)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (run_id, entity_type, entity_id, field_name, old_value, new_value),
    )
    conn.commit()
    conn.close()
