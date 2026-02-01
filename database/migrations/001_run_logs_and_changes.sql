-- Migration 001: Add run_logs and data_changes tables for Phase 4

CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('started', 'success', 'failure')),
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    finished_at TEXT,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS data_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_log_id INTEGER REFERENCES run_logs(id) ON DELETE SET NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    notified INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_data_changes_notified ON data_changes(notified);
CREATE INDEX IF NOT EXISTS idx_run_logs_script ON run_logs(script_name, started_at);
