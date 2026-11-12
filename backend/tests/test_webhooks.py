import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(db, monkeypatch):
    import app.main
    import app.services.sync_service as sync_service

    importlib.reload(app.main)

    class FakeStrava:
        def get_activity(self, activity_id):
            return {
                "id": activity_id,
                "name": "Run",
                "sport_type": "Run",
                "start_date": "2026-11-10T08:00:00Z",
                "distance": 5000,
                "moving_time": 1500,
                "elapsed_time": 1500,
            }

    monkeypatch.setattr(sync_service, "StravaClient", FakeStrava)
    return TestClient(app.main.app), db.get_conn


EVENT = {
    "object_type": "activity",
    "object_id": 42,
    "aspect_type": "create",
    "owner_id": 1,
    "event_time": 100,
}


def _ids(get_conn):
    conn = get_conn()
    try:
        return [r["id"] for r in conn.execute("SELECT id FROM activities")]
    finally:
        conn.close()


def _events(get_conn):
    conn = get_conn()
    try:
        return [tuple(r) for r in conn.execute("SELECT COUNT(*), MAX(processed) FROM webhook_events")][0]
    finally:
        conn.close()


def test_create_ingests_activity_and_marks_processed(client):
    c, get_conn = client
    assert c.post("/api/webhooks/strava", json=EVENT).json() == {"stored": True, "duplicate": False}
    assert _ids(get_conn) == [42]
    assert _events(get_conn) == (1, 1)


def test_retried_event_is_deduplicated(client):
    c, get_conn = client
    c.post("/api/webhooks/strava", json=EVENT)
    assert c.post("/api/webhooks/strava", json=EVENT).json()["duplicate"] is True
    assert _events(get_conn)[0] == 1


def test_delete_removes_activity(client):
    c, get_conn = client
    c.post("/api/webhooks/strava", json=EVENT)
    c.post("/api/webhooks/strava", json={**EVENT, "aspect_type": "delete", "event_time": 101})
    assert _ids(get_conn) == []


def test_owner_mismatch_ignored(client, monkeypatch):
    c, get_conn = client
    import app.services.webhook_service as webhook_service

    monkeypatch.setattr(webhook_service.settings, "STRAVA_ATHLETE_ID", "999")
    c.post("/api/webhooks/strava", json=EVENT)
    assert _ids(get_conn) == []


def test_failure_leaves_event_unprocessed_and_sets_error(client, monkeypatch):
    c, get_conn = client
    import app.services.webhook_service as webhook_service

    def boom(_):
        raise RuntimeError("strava down")

    monkeypatch.setattr(webhook_service, "ingest_single_activity", boom)
    assert c.post("/api/webhooks/strava", json=EVENT).status_code == 200
    assert _events(get_conn) == (1, 0)
    assert "strava down" in c.get("/api/admin/status").json()["last_error"]["value"]


def test_invalid_body_returns_422(client):
    c, _ = client
    assert c.post("/api/webhooks/strava", json=[1, 2]).status_code == 422
