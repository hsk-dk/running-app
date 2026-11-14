import json
import re
import sqlite3
from app.config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    name TEXT,
    sport_type TEXT,
    start_date TEXT,
    start_date_local TEXT,
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
    user_id INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'strava',
    source_id TEXT,
    garmin_id INTEGER,
    route_polyline TEXT,
    profile_json TEXT,
    laps_json TEXT,
    fit_status TEXT,
    is_extra INTEGER DEFAULT 0,
    is_aborted INTEGER DEFAULT 0,
    matched_planned_run_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    user_id INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'manual',
    external_uid TEXT,
    FOREIGN KEY (matched_activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'family',
    sharing_level TEXT NOT NULL DEFAULT 'private',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS strava_accounts (
    user_id INTEGER PRIMARY KEY,
    athlete_id TEXT NOT NULL UNIQUE,
    refresh_token TEXT NOT NULL,
    access_token TEXT,
    access_expires_at INTEGER,
    scope TEXT,
    connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS smashrun_accounts (
    user_id INTEGER PRIMARY KEY,
    refresh_token TEXT NOT NULL,
    access_token TEXT,
    access_expires_at INTEGER,
    scope TEXT,
    connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS garmin_accounts (
    user_id INTEGER PRIMARY KEY,
    api_key TEXT NOT NULL,
    bearer_token TEXT,
    token_expires_at INTEGER,
    connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS calendar_feeds (
    user_id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'runna',
    url TEXT NOT NULL,
    connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_state (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, key)
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
    user_id INTEGER,
    processed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    processed_at TEXT
);
"""

SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

BUSY_TIMEOUT_MS = 5000


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    # Per-connection settings (SQLite does not persist these).
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    return conn


# ---- migrations ------------------------------------------------------------
#
# The schema version is stored in SQLite's ``PRAGMA user_version``. SCHEMA_SQL
# above creates the current tables on a fresh database; migrations bring older
# databases up to date. Every migration must be idempotent, because a fresh
# database already contains its changes. To change the schema: update
# SCHEMA_SQL if needed, append a function to MIGRATIONS, never edit old ones.

# Columns that older databases may lack: (table, column, definition).
_COLUMNS_ADDED_IN_V1 = [
    ("planned_runs", "target_type", "TEXT DEFAULT 'time'"),
    ("planned_runs", "target_value", "REAL"),
    ("planned_runs", "mandatory", "INTEGER DEFAULT 1"),
    ("planned_runs", "manual_override", "INTEGER DEFAULT 0"),
    ("planned_runs", "override_reason", "TEXT"),
    ("planned_runs", "matched_activity_date", "TEXT"),
    ("planned_runs", "matched_activity_name", "TEXT"),
    ("planned_runs", "actual_value", "REAL"),
    ("planned_runs", "evaluated_at", "TEXT"),
    ("planned_runs", "match_score", "REAL"),
    ("planned_runs", "match_reason", "TEXT"),
    ("activities", "is_extra", "INTEGER DEFAULT 0"),
    ("activities", "is_aborted", "INTEGER DEFAULT 0"),
    ("activities", "matched_planned_run_id", "INTEGER"),
]


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    if not SAFE_IDENTIFIER_RE.match(table):
        raise ValueError(f"Unsafe table identifier: {table}")
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        is not None
    )


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    # Identifiers and definitions come only from the constant lists in this file.
    if not (SAFE_IDENTIFIER_RE.match(table) and SAFE_IDENTIFIER_RE.match(column)):
        raise ValueError(f"Unsafe identifier: {table}.{column}")
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migration_1_add_missing_columns(conn: sqlite3.Connection) -> None:
    for table, column, definition in _COLUMNS_ADDED_IN_V1:
        _add_column_if_missing(conn, table, column, definition)


def _migration_2_add_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_activities_start_date
            ON activities(start_date);
        CREATE INDEX IF NOT EXISTS idx_activities_matched_planned_run_id
            ON activities(matched_planned_run_id);
        CREATE INDEX IF NOT EXISTS idx_planned_runs_planned_date
            ON planned_runs(planned_date);
        CREATE INDEX IF NOT EXISTS idx_planned_runs_matched_activity_id
            ON planned_runs(matched_activity_id);
        CREATE INDEX IF NOT EXISTS idx_webhook_events_lookup
            ON webhook_events(object_type, object_id, aspect_type, event_time);
        """
    )


def _migration_3_clear_dangling_activity_refs(conn: sqlite3.Connection) -> None:
    """Foreign keys are enforced from now on; drop references to activities that no longer exist."""
    conn.execute(
        """
        UPDATE planned_runs
        SET
            matched_activity_id = NULL,
            matched_activity_date = NULL,
            matched_activity_name = NULL,
            actual_value = NULL,
            match_score = NULL,
            match_reason = NULL
        WHERE matched_activity_id IS NOT NULL
          AND matched_activity_id NOT IN (SELECT id FROM activities)
        """
    )
    if _table_exists(conn, "derived_metrics"):
        conn.execute("DELETE FROM derived_metrics WHERE activity_id NOT IN (SELECT id FROM activities)")


def _migration_4_add_start_date_local(conn: sqlite3.Connection) -> None:
    """Strava's local start time, used for all calendar logic. Backfilled from the stored raw JSON."""
    _add_column_if_missing(conn, "activities", "start_date_local", "TEXT")
    rows = conn.execute(
        "SELECT id, raw_json FROM activities WHERE start_date_local IS NULL"
    ).fetchall()
    updates = []
    for row in rows:
        try:
            local = json.loads(row["raw_json"]).get("start_date_local")
        except (TypeError, ValueError, AttributeError):
            local = None
        if local:
            updates.append((local, row["id"]))
    conn.executemany("UPDATE activities SET start_date_local = ? WHERE id = ?", updates)


def _migration_5_sync_mandatory_from_optional(conn: sqlite3.Connection) -> None:
    """`mandatory` becomes the single source of truth.

    Older code edited only `optional`, so where both are set `optional` is the newer value.
    """
    conn.execute(
        "UPDATE planned_runs SET mandatory = CASE WHEN optional = 1 THEN 0 ELSE 1 END "
        "WHERE optional IS NOT NULL"
    )


def _migration_6_drop_derived_metrics(conn: sqlite3.Connection) -> None:
    """Never populated or read."""
    conn.execute("DROP TABLE IF EXISTS derived_metrics")


DEFAULT_USER_ID = 1
_USER_STATE_KEYS = ("last_sync_at", "last_ingest_result", "last_error", "last_synced_start_date")


def _migration_7_users(conn: sqlite3.Connection) -> None:
    """Multiple users. All existing data belongs to the first user (the owner), who is created here."""
    for table, definition in (
        ("activities", "INTEGER NOT NULL DEFAULT 1"),
        ("planned_runs", "INTEGER NOT NULL DEFAULT 1"),
        ("webhook_events", "INTEGER"),
    ):
        _add_column_if_missing(conn, table, "user_id", definition)

    conn.execute(
        """
        INSERT OR IGNORE INTO users (id, external_id, username, display_name, role)
        VALUES (?, 'local', 'owner', 'Mig', 'admin')
        """,
        (DEFAULT_USER_ID,),
    )

    # Per-user keys move out of the global sync_state table.
    placeholders = ", ".join("?" for _ in _USER_STATE_KEYS)
    conn.execute(
        f"INSERT OR IGNORE INTO user_state (user_id, key, value, updated_at) "
        f"SELECT ?, key, value, updated_at FROM sync_state WHERE key IN ({placeholders})",
        (DEFAULT_USER_ID, *_USER_STATE_KEYS),
    )
    conn.execute(f"DELETE FROM sync_state WHERE key IN ({placeholders})", _USER_STATE_KEYS)

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_activities_user_start ON activities(user_id, start_date);
        CREATE INDEX IF NOT EXISTS idx_planned_runs_user_date ON planned_runs(user_id, planned_date);
        CREATE INDEX IF NOT EXISTS idx_webhook_events_user ON webhook_events(user_id);
        """
    )


def _migration_8_splits(conn: sqlite3.Connection) -> None:
    """Kilometre splits are fetched from Strava once per run on demand and cached here (NULL = not fetched yet)."""
    _add_column_if_missing(conn, "activities", "splits_json", "TEXT")


def _migration_9_sources(conn: sqlite3.Connection) -> None:
    """Runs can come from more than one place. Strava ids are positive; Smashrun runs are stored as -id."""
    _add_column_if_missing(conn, "activities", "source", "TEXT NOT NULL DEFAULT 'strava'")
    _add_column_if_missing(conn, "activities", "source_id", "TEXT")
    conn.execute("UPDATE activities SET source_id = CAST(id AS TEXT) WHERE source_id IS NULL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS smashrun_accounts (
            user_id INTEGER PRIMARY KEY,
            refresh_token TEXT NOT NULL,
            access_token TEXT,
            access_expires_at INTEGER,
            scope TEXT,
            connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_user_start ON activities(user_id, start_date)")


def _migration_10_plan_import(conn: sqlite3.Connection) -> None:
    """Planned runs can be imported from the person's Runna calendar link and are then kept in step with it."""
    _add_column_if_missing(conn, "planned_runs", "source", "TEXT NOT NULL DEFAULT 'manual'")
    _add_column_if_missing(conn, "planned_runs", "external_uid", "TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calendar_feeds (
            user_id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL DEFAULT 'runna',
            url TEXT NOT NULL,
            connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_planned_external ON planned_runs(user_id, external_uid) "
        "WHERE external_uid IS NOT NULL"
    )


def _migration_11_garmin(conn: sqlite3.Connection) -> None:
    """Garmin Connect (personal API) as a source: a run can be linked to its Garmin activity, and what the FIT file
    tells about it (route, per-second profile, laps) is kept with the run. fit_status: NULL = not read yet,
    'ok' = read, 'none' = Garmin has no usable file for it."""
    for column, definition in (
        ("garmin_id", "INTEGER"),
        ("route_polyline", "TEXT"),
        ("profile_json", "TEXT"),
        ("laps_json", "TEXT"),
        ("fit_status", "TEXT"),
    ):
        _add_column_if_missing(conn, "activities", column, definition)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS garmin_accounts (
            user_id INTEGER PRIMARY KEY,
            api_key TEXT NOT NULL,
            bearer_token TEXT,
            token_expires_at INTEGER,
            connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_garmin ON activities(user_id, garmin_id)")


def _migration_12_drop_strava(conn: sqlite3.Connection) -> None:
    """Strava's API is closed to the app, so its connection is gone: drop the stored Strava tokens and the webhook log.
    The runs that came from Strava stay (source = 'strava'), with their routes."""
    conn.execute("DROP TABLE IF EXISTS strava_accounts")
    conn.execute("DROP TABLE IF EXISTS webhook_events")
    conn.execute("DELETE FROM sync_state WHERE key = 'last_webhook_at'")


def _migration_13_children(conn: sqlite3.Connection) -> None:
    """A parent can mark a family member as a child. A child sees a simpler app, and the parents see a short summary."""
    _add_column_if_missing(conn, "users", "is_child", "INTEGER NOT NULL DEFAULT 0")


MIGRATIONS = [
    _migration_1_add_missing_columns,
    _migration_2_add_indexes,
    _migration_3_clear_dangling_activity_refs,
    _migration_4_add_start_date_local,
    _migration_5_sync_mandatory_from_optional,
    _migration_6_drop_derived_metrics,
    _migration_7_users,
    _migration_8_splits,
    _migration_9_sources,
    _migration_10_plan_import,
    _migration_11_garmin,
    _migration_12_drop_strava,
    _migration_13_children,
]
SCHEMA_VERSION = len(MIGRATIONS)


def get_schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate_db() -> None:
    conn = get_conn()
    try:
        version = get_schema_version(conn)
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than this app supports ({SCHEMA_VERSION})"
            )
        for number, migration in enumerate(MIGRATIONS, start=1):
            if number <= version:
                continue
            migration(conn)
            conn.execute(f"PRAGMA user_version = {number}")
            conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    conn = get_conn()
    try:
        # WAL lets readers and the webhook writer work at the same time. The mode is
        # stored in the database file, so setting it once is enough.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

    migrate_db()
