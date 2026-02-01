"""Database helper for Streamlit pages."""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import DATABASE_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a query and return a DataFrame."""
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def execute(sql: str, params: tuple = ()):
    """Execute a write query."""
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
    conn.close()
