import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.conftest import add_activity, add_plan


def _raw(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def test_connection_pragmas(db):
    conn = db.get_conn()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 5000
    finally:
        conn.close()


def test_wal_mode_is_enabled(db):
    conn = db.get_conn()
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        conn.close()


def test_indexes_exist(db):
    conn = db.get_conn()
    try:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    finally:
        conn.close()
    assert {
        "idx_activities_start_date",
        "idx_activities_matched_planned_run_id",
        "idx_planned_runs_planned_date",
        "idx_planned_runs_matched_activity_id",
        "idx_webhook_events_lookup",
    } <= names


def test_fresh_db_is_at_latest_version(db):
    conn = db.get_conn()
    try:
        assert db.get_schema_version(conn) == db.SCHEMA_VERSION
    finally:
        conn.close()


def test_foreign_keys_are_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_plan(db, "2020-03-10", matched_activity_id=999)


def test_init_db_is_idempotent(db):
    add_activity(db, 1, "2020-03-10T08:00:00Z")
    db.init_db()
    db.init_db()
    conn = db.get_conn()
    try:
        assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 1
        assert db.get_schema_version(conn) == db.SCHEMA_VERSION
    finally:
        conn.close()


LEGACY_SCHEMA = """
CREATE TABLE activities (
    id INTEGER PRIMARY KEY, name TEXT, sport_type TEXT, start_date TEXT,
    timezone_name TEXT, distance_m REAL, moving_time_s INTEGER, elapsed_time_s INTEGER,
    total_elevation_gain REAL, average_speed REAL, max_speed REAL, average_heartrate REAL,
    max_heartrate REAL, average_cadence REAL, raw_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE planned_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, planned_date TEXT NOT NULL, session_type TEXT NOT NULL,
    target_minutes INTEGER, optional INTEGER DEFAULT 0, notes TEXT,
    matched_activity_id INTEGER, status TEXT DEFAULT 'planlagt',
    FOREIGN KEY (matched_activity_id) REFERENCES activities(id)
);
CREATE TABLE derived_metrics (
    activity_id INTEGER PRIMARY KEY, start_date TEXT NOT NULL, year INTEGER NOT NULL,
    month_key TEXT NOT NULL, iso_week_key TEXT NOT NULL
);
INSERT INTO activities (id, sport_type, start_date, raw_json) VALUES (1, 'Run', '2020-03-10T08:00:00Z', '{}');
INSERT INTO planned_runs (planned_date, session_type, matched_activity_id) VALUES ('2020-03-10', 'easy', 1);
INSERT INTO planned_runs (planned_date, session_type, matched_activity_id) VALUES ('2020-03-11', 'easy', 999);
INSERT INTO derived_metrics VALUES (999, '2020-01-01', 2020, '2020-01', '2020-W01');
"""


def test_legacy_database_is_upgraded(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    raw = _raw(path)
    raw.executescript(LEGACY_SCHEMA)
    raw.commit()
    raw.close()

    monkeypatch.setenv("DATABASE_PATH", str(path))
    import app.config
    import app.db

    importlib.reload(app.config)
    importlib.reload(app.db)
    app.db.init_db()

    conn = app.db.get_conn()
    try:
        assert app.db.get_schema_version(conn) == app.db.SCHEMA_VERSION
        for column in ("target_type", "mandatory", "manual_override", "match_score"):
            assert app.db.column_exists(conn, "planned_runs", column)
        for column in ("is_extra", "matched_planned_run_id"):
            assert app.db.column_exists(conn, "activities", column)

        plans = conn.execute("SELECT matched_activity_id FROM planned_runs ORDER BY id").fetchall()
        assert [p[0] for p in plans] == [1, None]  # valid link kept, dangling link cleared
        assert conn.execute("SELECT COUNT(*) FROM derived_metrics").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 1
    finally:
        conn.close()


def test_newer_database_is_refused(db):
    conn = db.get_conn()
    try:
        conn.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError):
        db.migrate_db()


# ---- startup ----------------------------------------------------------------

def test_importing_main_has_no_side_effects(tmp_path, monkeypatch):
    path = tmp_path / "import.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    import app.config
    import app.db
    import app.main

    importlib.reload(app.config)
    importlib.reload(app.db)
    importlib.reload(app.main)

    assert not path.exists()


def test_lifespan_initialises_database_and_links(tmp_path, monkeypatch):
    path = tmp_path / "startup.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    import app.config
    import app.db
    import app.main

    importlib.reload(app.config)
    importlib.reload(app.db)
    importlib.reload(app.main)

    with TestClient(app.main.app) as client:
        assert path.exists()
        assert client.get("/api/admin/health").json() == {"ok": True, "mismatch_count": 0}
        conn = app.db.get_conn()
        try:
            assert app.db.get_schema_version(conn) == app.db.SCHEMA_VERSION
        finally:
            conn.close()
