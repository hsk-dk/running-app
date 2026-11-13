import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Fresh SQLite database per test. Returns the app.db module."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("STRAVA_ATHLETE_ID", "")

    import app.config
    import app.db

    importlib.reload(app.config)
    importlib.reload(app.db)
    app.db.init_db()
    return app.db


def add_activity(db, id, start_date, distance_m=5000, moving_time_s=1800, name="Run", sport_type="Run", raw=None, user_id=1):
    conn = db.get_conn()
    try:
        conn.execute(
            """
            INSERT INTO activities (id, name, sport_type, start_date, distance_m, moving_time_s, raw_json, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id, name, sport_type, start_date, distance_m, moving_time_s, json.dumps(raw if raw is not None else {}), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def add_plan(
    db,
    planned_date,
    session_type="easy",
    target_type="time",
    target_value=30,
    mandatory=1,
    status="planlagt",
    manual_override=0,
    matched_activity_id=None,
    user_id=1,
):
    conn = db.get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO planned_runs (
                planned_date, session_type, target_type, target_value,
                mandatory, optional, status, manual_override, matched_activity_id, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                planned_date, session_type, target_type, target_value,
                mandatory, int(not mandatory), status, manual_override, matched_activity_id, user_id,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_plan(db, plan_id):
    conn = db.get_conn()
    try:
        return dict(conn.execute("SELECT * FROM planned_runs WHERE id = ?", (plan_id,)).fetchone())
    finally:
        conn.close()


def get_activity(db, activity_id):
    conn = db.get_conn()
    try:
        return dict(conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone())
    finally:
        conn.close()


def connect_strava(db, user_id=1, athlete_id="1"):
    """Give a user a Strava account (webhook events are routed by athlete id)."""
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO strava_accounts (user_id, athlete_id, refresh_token) VALUES (?, ?, 'refresh')",
            (user_id, str(athlete_id)),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def proxy(db, monkeypatch):
    """The app in proxy mode, called from a trusted address, with no one signed in until headers are sent."""
    import importlib

    from fastapi.testclient import TestClient

    import app.main
    from tests.auth_helpers import PROXY_IP, FromAddress, patch_settings

    importlib.reload(app.main)
    patch_settings(monkeypatch, AUTH_MODE="proxy", TRUSTED_PROXIES=["10.0.0.0/8"], AUTH_OWNER_USERNAME="")
    return TestClient(FromAddress(app.main.app, PROXY_IP), follow_redirects=False)
