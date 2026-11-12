import importlib
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import add_activity, add_plan


@pytest.fixture()
def client(db):
    import app.matching, app.metrics, app.planning, app.ai_suggestions, app.admin_status
    import app.services.planning_service, app.main

    for mod in (
        app.matching, app.metrics, app.planning, app.ai_suggestions,
        app.admin_status, app.services.planning_service, app.main,
    ):
        importlib.reload(mod)
    return TestClient(app.main.app)


def test_planning_crud_roundtrip(client):
    created = client.post(
        "/api/planning",
        json={"planned_date": "2100-01-01", "session_type": "easy", "target_type": "time", "target_value": 40},
    ).json()
    assert created["status"] == "planlagt"
    assert [p["id"] for p in client.get("/api/planning").json()] == [created["id"]]

    client.put(
        f"/api/planning/{created['id']}",
        json={
            "planned_date": "2100-01-02", "session_type": "long",
            "target_type": "distance", "target_value": 15,
        },
    )
    plan = client.get("/api/planning").json()[0]
    assert (plan["session_type"], plan["manual_override"]) == ("long", True)

    assert client.delete(f"/api/planning/{created['id']}").json() == {"deleted": created["id"]}
    assert client.get("/api/planning").json() == []


def test_manual_match_skip_and_clear(client, db):
    plan = add_plan(db, "2020-03-10", target_value=30)
    add_activity(db, 1, "2020-03-10T08:00:00Z", moving_time_s=1800)
    add_activity(db, 2, "2020-03-10T18:00:00Z", moving_time_s=600)

    client.post(f"/api/planning/{plan}/match-activity", json={"activity_id": 2})
    p = client.get("/api/planning").json()[0]
    assert (p["matched_activity_id"], p["status"]) == (2, "sprunget over")

    client.post(f"/api/planning/{plan}/clear-match")
    p = client.get("/api/planning").json()[0]
    assert p["matched_activity_id"] is None

    client.post(f"/api/planning/{plan}/mark-skipped")
    assert client.get("/api/planning").json()[0]["status"] == "sprunget over"
    assert client.get("/api/admin/health").json() == {"ok": True, "mismatch_count": 0}


def test_activities_and_metrics(client, db):
    today = date.today()
    add_activity(db, 1, f"{today.isoformat()}T08:00:00Z", distance_m=10000, moving_time_s=3000)
    add_activity(db, 2, f"{today.isoformat()}T09:00:00Z", sport_type="Ride")

    acts = client.get("/api/activities").json()
    assert [a["id"] for a in acts] == [1]
    assert acts[0]["distance_km"] == 10.0

    summary = client.get("/api/metrics/summary").json()
    assert summary["km_this_month"] == 10.0
    assert summary["runs_this_month"] == 1
    monthly = client.get("/api/metrics/monthly-volume").json()
    assert monthly[0]["km"] == 10.0


def test_metrics_empty(client):
    assert client.get("/api/metrics/summary").json()["runs_this_month"] == 0
    assert client.get("/api/metrics/monthly-volume").json() == []
    assert client.get("/api/planning/weekly-consistency").json() == []


def test_admin_status_and_health(client):
    status = client.get("/api/admin/status").json()
    assert status["webhook_event_count"] == 0
    assert client.get("/api/admin/health").json()["ok"] is True


def test_ai_context_queries(db):
    import app.ai_suggestions as ai

    today = date.today()
    add_activity(db, 1, f"{today.isoformat()}T08:00:00Z", distance_m=8000, moving_time_s=2400)
    add_plan(db, (today + timedelta(days=2)).isoformat(), target_value=30)

    runs = ai._get_recent_activities(weeks=2)
    assert [r["distance_km"] for r in runs] == [8.0]
    assert len(ai._get_current_planned_runs()) == 1


# ---- sprint 5: local dates, partial credit, single mandatory flag ----------------

def _set_today(monkeypatch, day):
    from app.domain import timeutil

    monkeypatch.setattr(timeutil, "today", lambda: day)


def _add_local(db, id, utc, local, distance_m=10000):
    import json

    conn = db.get_conn()
    try:
        conn.execute(
            """INSERT INTO activities (id, name, sport_type, start_date, start_date_local,
                                       distance_m, moving_time_s, raw_json)
               VALUES (?, 'Run', 'Run', ?, ?, ?, 3000, ?)""",
            (id, utc, local, distance_m, json.dumps({})),
        )
        conn.commit()
    finally:
        conn.close()


def test_month_is_decided_by_local_date(client, db, monkeypatch):
    _set_today(monkeypatch, date(2020, 3, 15))
    # 23:30 UTC on 29 Feb is 00:30 on 1 March locally: it belongs to March
    _add_local(db, 1, "2020-02-29T23:30:00Z", "2020-03-01T00:30:00Z", distance_m=10000)
    _add_local(db, 2, "2020-02-20T08:00:00Z", "2020-02-20T09:00:00Z", distance_m=5000)

    summary = client.get("/api/metrics/summary").json()
    assert (summary["runs_this_month"], summary["km_this_month"]) == (1, 10.0)
    assert (summary["runs_prev_month"], summary["km_prev_month"]) == (1, 5.0)
    assert client.get("/api/metrics/monthly-volume").json() == [
        {"month": "2020-02", "km": 5.0},
        {"month": "2020-03", "km": 10.0},
    ]
    assert client.get("/api/activities").json()[0]["date"] == "2020-03-01"


def test_previous_month_wraps_over_new_year(client, db, monkeypatch):
    _set_today(monkeypatch, date(2020, 1, 15))
    _add_local(db, 1, "2019-12-20T08:00:00Z", "2019-12-20T09:00:00Z")

    assert client.get("/api/metrics/summary").json()["runs_prev_month"] == 1


def test_adherence_gives_partial_credit_and_matches_consistency(client, db, monkeypatch):
    _set_today(monkeypatch, date(2020, 3, 12))  # Thursday, ISO week 2020-W11
    add_plan(db, "2020-03-09", status="gennemført")
    add_plan(db, "2020-03-10", status="forkortet")
    add_plan(db, "2020-03-12", status="planlagt")  # still open
    add_plan(db, "2020-03-11", status="sprunget over", mandatory=0)  # optional: ignored

    summary = client.get("/api/metrics/summary").json()
    assert summary["adherence_pct_current_week"] == 75
    assert (summary["current_week_completed"], summary["current_week_shortened"]) == (1, 1)
    assert (summary["current_week_relevant"], summary["current_week_awaiting"]) == (2, 1)

    week = next(w for w in client.get("/api/planning/weekly-consistency").json() if w["week"] == "2020-W11")
    assert (week["completed"], week["shortened"], week["relevant_runs"]) == (1, 1, 2)
    assert week["score"] == "Gul"


def test_editing_optional_updates_mandatory(client, db):
    plan = add_plan(db, "2100-01-05", mandatory=1)
    client.put(
        f"/api/planning/{plan}",
        json={
            "planned_date": "2100-01-05", "session_type": "easy",
            "target_type": "time", "target_value": 30, "optional": True,
        },
    )
    row = client.get("/api/planning").json()[0]
    assert (row["mandatory"], row["optional"]) == (False, True)
    # optional runs do not count towards consistency
    assert client.get("/api/planning/weekly-consistency").json() == []

    client.put(
        f"/api/planning/{plan}",
        json={
            "planned_date": "2100-01-05", "session_type": "easy",
            "target_type": "time", "target_value": 30, "optional": False,
        },
    )
    assert client.get("/api/planning").json()[0]["mandatory"] is True
    assert len(client.get("/api/planning/weekly-consistency").json()) == 1
