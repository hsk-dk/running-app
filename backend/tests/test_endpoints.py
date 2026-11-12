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
