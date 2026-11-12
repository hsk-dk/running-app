import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(db):
    import app.main

    importlib.reload(app.main)
    return TestClient(app.main.app)


def test_route_table_is_unchanged(client):
    schema = client.get("/openapi.json").json()
    routes = {
        (method.upper(), path)
        for path, methods in schema["paths"].items()
        for method in methods
    }
    assert routes >= {
        ("GET", "/api/health"),
        ("GET", "/api/activities"),
        ("GET", "/api/metrics/summary"),
        ("GET", "/api/metrics/monthly-volume"),
        ("GET", "/api/planning"),
        ("GET", "/api/planning/weekly-consistency"),
        ("POST", "/api/planning"),
        ("POST", "/api/planning/evaluate"),
        ("POST", "/api/planning/{planned_run_id}/mark-skipped"),
        ("POST", "/api/planning/{planned_run_id}/mark-rescheduled"),
        ("POST", "/api/planning/{planned_run_id}/clear-match"),
        ("POST", "/api/planning/{planned_run_id}/match-activity"),
        ("PUT", "/api/planning/{planned_run_id}"),
        ("DELETE", "/api/planning/{planned_run_id}"),
        ("GET", "/api/ai/suggestions"),
        ("GET", "/api/admin/status"),
        ("POST", "/api/admin/ingest"),
        ("POST", "/api/admin/rebuild-metrics"),
        ("POST", "/api/admin/recalculate-plan"),
        ("POST", "/api/admin/rebuild-links"),
        ("GET", "/api/admin/health"),
        ("GET", "/api/webhooks/strava"),
        ("POST", "/api/webhooks/strava"),
    }


def test_webhook_verify_accepts_correct_token(client, monkeypatch):
    import app.webhooks

    monkeypatch.setattr(app.webhooks.settings, "STRAVA_VERIFY_TOKEN", "secret")
    params = {"hub.mode": "subscribe", "hub.verify_token": "secret", "hub.challenge": "abc"}
    r = client.get("/api/webhooks/strava", params=params)
    assert r.status_code == 200 and r.json() == {"hub.challenge": "abc"}


def test_webhook_verify_rejects_wrong_token(client, monkeypatch):
    import app.webhooks

    monkeypatch.setattr(app.webhooks.settings, "STRAVA_VERIFY_TOKEN", "secret")
    params = {"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "abc"}
    assert client.get("/api/webhooks/strava", params=params).status_code == 403


def test_webhook_verify_requires_query_params(client):
    assert client.get("/api/webhooks/strava").status_code == 422


def test_webhook_rejects_invalid_json(client):
    r = client.post("/api/webhooks/strava", content="not json", headers={"content-type": "application/json"})
    assert r.status_code == 400


def test_match_activity_requires_activity_id(client):
    r = client.post("/api/planning/1/match-activity", json={})
    assert r.status_code == 400
    assert r.json()["detail"] == "activity_id is required"


def test_ingest_failure_is_recorded_and_raised(client, monkeypatch):
    import app.services.admin_service as admin_service

    def boom(pages):
        raise RuntimeError("strava down")

    monkeypatch.setattr(admin_service, "ingest_recent", boom)
    with pytest.raises(RuntimeError):
        TestClient(client.app, raise_server_exceptions=True).post("/api/admin/ingest")
    assert "strava down" in client.get("/api/admin/status").json()["last_error"]["value"]
