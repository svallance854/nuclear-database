"""Shared database utilities for ingestion scripts."""
import sqlite3
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection with foreign keys enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database from schema and seed files if it doesn't exist, then apply migrations."""
    db_path = Path(DATABASE_PATH)
    base = Path(__file__).resolve().parent.parent
    if not db_path.exists():
        conn = sqlite3.connect(str(db_path))
        with open(base / "database" / "schema.sql") as f:
            conn.executescript(f.read())
        with open(base / "database" / "seed_data.sql") as f:
            conn.executescript(f.read())
        conn.close()
        logging.info("Database initialized at %s", db_path)
    _apply_migrations(base)


def _apply_migrations(base: Path):
    """Apply any pending migration files from database/migrations/ in sorted order."""
    migrations_dir = base / "database" / "migrations"
    if not migrations_dir.exists():
        return
    conn = sqlite3.connect(DATABASE_PATH)
    # Track applied migrations
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))")
    applied = {r[0] for r in conn.execute("SELECT name FROM _migrations").fetchall()}
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        if sql_file.name not in applied:
            logging.info("Applying migration: %s", sql_file.name)
            with open(sql_file) as f:
                conn.executescript(f.read())
            conn.execute("INSERT INTO _migrations (name) VALUES (?)", (sql_file.name,))
            conn.commit()
    conn.close()


def setup_logging(name: str) -> logging.Logger:
    """Configure and return a logger for a script."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        ))
        logger.addHandler(handler)
    return logger
