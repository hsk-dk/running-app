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
        ("POST", "/api/admin/recalculate-plan"),
        ("POST", "/api/admin/rebuild-links"),
        ("GET", "/api/admin/health"),
        ("GET", "/api/webhooks/strava"),
        ("POST", "/api/webhooks/strava"),
    }


def test_rebuild_metrics_endpoint_is_gone(client):
    assert client.post("/api/admin/rebuild-metrics").status_code in (404, 405)


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
    assert r.status_code == 422


def test_webhook_accepts_partial_and_extra_fields(client):
    r = client.post("/api/webhooks/strava", json={"object_type": "athlete", "something_new": 1})
    assert r.status_code == 200 and r.json()["stored"] is True


def test_match_activity_requires_activity_id(client):
    r = client.post("/api/planning/1/match-activity", json={})
    assert r.status_code == 422
    assert "activity_id" in r.json()["detail"]


def test_ingest_failure_is_recorded_and_raised(client, monkeypatch):
    import app.services.admin_service as admin_service

    def boom(pages):
        raise RuntimeError("strava down")

    monkeypatch.setattr(admin_service, "ingest_recent", boom)
    with pytest.raises(RuntimeError):
        TestClient(client.app, raise_server_exceptions=True).post("/api/admin/ingest")
    assert "strava down" in client.get("/api/admin/status").json()["last_error"]["value"]


# ---- validation (422) and not found (404) ---------------------------------

VALID = {"planned_date": "2100-01-01", "session_type": "easy", "target_type": "time", "target_value": 30}


@pytest.mark.parametrize(
    "patch",
    [
        {"planned_date": "not-a-date"},
        {"planned_date": ""},
        {"session_type": "  "},
        {"target_type": "swim"},
        {"target_value": -5},
        {"target_value": "abc"},
    ],
)
def test_create_rejects_invalid_input(client, patch):
    r = client.post("/api/planning", json={**VALID, **patch})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)  # frontend prints it verbatim


def test_create_rejects_missing_required_fields(client):
    r = client.post("/api/planning", json={"session_type": "easy"})
    assert r.status_code == 422
    assert "planned_date" in r.json()["detail"]


def test_create_accepts_ai_style_payload(client):
    r = client.post(
        "/api/planning",
        json={**VALID, "target_value": 0, "optional": True, "notes": None, "extra": "ignored"},
    )
    assert r.status_code == 200
    assert r.json()["mandatory"] is False


def test_create_accepts_datetime_string(client):
    assert client.post("/api/planning", json={**VALID, "planned_date": "2100-01-01T07:30:00"}).status_code == 200


def test_update_requires_target_fields(client):
    created = client.post("/api/planning", json=VALID).json()
    r = client.put(f"/api/planning/{created['id']}", json={"planned_date": "2100-01-02", "session_type": "easy"})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("put", "/api/planning/999", VALID),
        ("delete", "/api/planning/999", None),
        ("post", "/api/planning/999/mark-skipped", None),
        ("post", "/api/planning/999/mark-rescheduled", None),
        ("post", "/api/planning/999/clear-match", None),
        ("post", "/api/planning/999/match-activity", {"activity_id": 1}),
    ],
)
def test_unknown_plan_returns_404(client, method, path, body):
    r = getattr(client, method)(path, **({"json": body} if body is not None else {}))
    assert r.status_code == 404
    assert "999" in r.json()["detail"]


def test_match_unknown_activity_returns_404(client):
    created = client.post("/api/planning", json=VALID).json()
    r = client.post(f"/api/planning/{created['id']}/match-activity", json={"activity_id": 12345})
    assert r.status_code == 404
    assert "12345" in r.json()["detail"]


@pytest.mark.parametrize("value", [0, -1, 501, "x"])
def test_activities_limit_is_bounded(client, value):
    assert client.get("/api/activities", params={"limit": value}).status_code == 422


def test_activities_limit_accepts_valid(client):
    assert client.get("/api/activities", params={"limit": 500}).status_code == 200


def test_ingest_pages_is_bounded(client):
    assert client.post("/api/admin/ingest", params={"pages": 999}).status_code == 422


def test_unhandled_error_is_logged_and_hides_details(client, monkeypatch):
    import app.services.planning_service as planning_service

    def boom():
        raise RuntimeError("secret internals")

    monkeypatch.setattr(planning_service, "list_planned_runs", boom)
    c = TestClient(client.app, raise_server_exceptions=False)
    r = c.get("/api/planning")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error"}
