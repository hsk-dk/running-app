import sqlite3
import re
from app.config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    name TEXT,
    sport_type TEXT,
    start_date TEXT,
    timezone_name TEXT,
    distance_m REAL,
    moving_time_s INTEGER,
    elapsed_time_s INTEGER,
    total_elevation_gain REAL,
    average_speed REAL,
    max_speed REAL,
    average_heartrate REAL,
    max_heartrate REAL,
    average_cadence REAL,
    raw_json TEXT NOT NULL,
    is_extra INTEGER DEFAULT 0,
    is_aborted INTEGER DEFAULT 0,
    matched_planned_run_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS derived_metrics (
    activity_id INTEGER PRIMARY KEY,
    start_date TEXT NOT NULL,
    year INTEGER NOT NULL,
    month_key TEXT NOT NULL,
    iso_week_key TEXT NOT NULL,
    distance_km REAL,
    moving_minutes REAL,
    pace_sec_per_km REAL,
    average_heartrate REAL,
    hr_efficiency REAL,
    easy_aerobic_flag INTEGER,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS planned_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planned_date TEXT NOT NULL,
    session_type TEXT NOT NULL,
    target_minutes INTEGER,
    optional INTEGER DEFAULT 0,
    notes TEXT,
    matched_activity_id INTEGER,
    matched_activity_date TEXT,
    matched_activity_name TEXT,
    actual_value REAL,
    status TEXT DEFAULT 'planlagt',
    target_type TEXT DEFAULT 'time',
    target_value REAL,
    mandatory INTEGER DEFAULT 1,
    manual_override INTEGER DEFAULT 0,
    override_reason TEXT,
    evaluated_at TEXT,
    match_score REAL,
    match_reason TEXT,
    FOREIGN KEY (matched_activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    object_type TEXT,
    object_id TEXT,
    aspect_type TEXT,
    owner_id TEXT,
    subscription_id TEXT,
    event_time INTEGER,
    payload_json TEXT NOT NULL,
    processed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    processed_at TEXT
);
"""

ALLOWED_MIGRATION_COLUMNS = {
    "planned_runs": {
        "target_type": "TEXT DEFAULT 'time'",
        "target_value": "REAL",
        "mandatory": "INTEGER DEFAULT 1",
        "manual_override": "INTEGER DEFAULT 0",
        "override_reason": "TEXT",
        "matched_activity_date": "TEXT",
        "matched_activity_name": "TEXT",
        "actual_value": "REAL",
        "evaluated_at": "TEXT",
        "match_score": "REAL",
        "match_reason": "TEXT",
    },
    "activities": {
        "is_extra": "INTEGER DEFAULT 0",
        "is_aborted": "INTEGER DEFAULT 0",
        "matched_planned_run_id": "INTEGER",
    },
}
SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    if table not in ALLOWED_MIGRATION_COLUMNS:
        raise ValueError(f"Unsupported table for migration: {table}")
    if not SAFE_IDENTIFIER_RE.match(table):
        raise ValueError(f"Unsafe table identifier: {table}")
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    expected_definition = ALLOWED_MIGRATION_COLUMNS.get(table, {}).get(column)
    if expected_definition != definition:
        raise ValueError(f"Unsupported column migration: {table}.{column}")
    if not column_exists(conn, table, column):
        # table/column/definition are constrained by ALLOWED_MIGRATION_COLUMNS and SAFE_IDENTIFIER_RE.
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_db() -> None:
    conn = get_conn()
    try:
        ensure_column(conn, "planned_runs", "target_type", "TEXT DEFAULT 'time'")
        ensure_column(conn, "planned_runs", "target_value", "REAL")
        ensure_column(conn, "planned_runs", "mandatory", "INTEGER DEFAULT 1")
        ensure_column(conn, "planned_runs", "manual_override", "INTEGER DEFAULT 0")
        ensure_column(conn, "planned_runs", "override_reason", "TEXT")
        ensure_column(conn, "planned_runs", "matched_activity_date", "TEXT")
        ensure_column(conn, "planned_runs", "matched_activity_name", "TEXT")
        ensure_column(conn, "planned_runs", "actual_value", "REAL")
        ensure_column(conn, "planned_runs", "evaluated_at", "TEXT")
        ensure_column(conn, "planned_runs", "match_score", "REAL")
        ensure_column(conn, "planned_runs", "match_reason", "TEXT")

        ensure_column(conn, "activities", "is_extra", "INTEGER DEFAULT 0")
        ensure_column(conn, "activities", "is_aborted", "INTEGER DEFAULT 0")
        ensure_column(conn, "activities", "matched_planned_run_id", "INTEGER")

        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

    migrate_db()
