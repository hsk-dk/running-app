"""Kilometre splits: parsed from Strava, fetched once, kept, and shared only the way runs are."""
import pytest

from app.domain.splits import parse_splits
from tests.auth_helpers import ADMIN, FAMILY
from tests.conftest import add_activity, connect_strava

STRAVA_SPLITS = [
    {"distance": 1000.0, "moving_time": 330, "elapsed_time": 335, "elevation_difference": 4.2, "split": 1},
    {"distance": 1000.0, "moving_time": 300, "elapsed_time": 300, "elevation_difference": -2.0, "split": 2},
    {"distance": 420.0, "moving_time": 130, "elapsed_time": 130, "elevation_difference": 0.0, "split": 3},
]


def test_parse_gives_a_row_per_kilometre_with_pace_and_marks_the_leftover():
    rows = parse_splits(STRAVA_SPLITS)
    assert [r["km"] for r in rows] == [1, 2, 3]
    assert rows[0]["pace_s_per_km"] == 330.0 and rows[1]["pace_s_per_km"] == 300.0
    assert rows[2]["pace_s_per_km"] == round(130 / 0.42, 1)
    assert [r["partial"] for r in rows] == [False, False, True]
    assert rows[1]["elevation_m"] == -2.0


@pytest.mark.parametrize("raw", [None, {}, "x", [], [None, 3, {"distance": 0, "moving_time": 10}, {"distance": "a"}]])
def test_parse_survives_missing_or_broken_data(raw):
    assert parse_splits(raw) == []


@pytest.fixture()
def two(proxy, db, monkeypatch):
    import app.services.sync_service as sync_service

    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    connect_strava(db, user_id=1, athlete_id="11")
    connect_strava(db, user_id=2, athlete_id="22")
    add_activity(db, 10, "2026-11-10T08:00:00Z", distance_m=2420, moving_time_s=760, user_id=1)
    add_activity(db, 20, "2026-11-10T08:00:00Z", distance_m=2420, moving_time_s=760, user_id=2)
    calls = []
    state = {"mode": "ok"}

    class FakeStrava:
        def __init__(self, refresh_token, access_token=None, access_expires_at=None, on_tokens=None):
            self.who = refresh_token

        def get_activity(self, activity_id):
            calls.append(activity_id)
            if state["mode"] == "down":
                raise RuntimeError("strava is down")
            if state["mode"] == "gone":
                return None
            return {"id": activity_id, "sport_type": "Run", "splits_metric": STRAVA_SPLITS}

    monkeypatch.setattr(sync_service, "StravaClient", FakeStrava)
    return proxy, calls, state


def test_splits_are_fetched_once_then_served_from_the_cache(two):
    client, calls, _ = two
    first = client.get("/api/activities/10/splits", headers=ADMIN).json()
    assert first["available"] is True and len(first["splits"]) == 3
    second = client.get("/api/activities/10/splits", headers=ADMIN).json()
    assert second == first and calls == [10]


def test_a_run_without_splits_is_cached_as_empty_not_refetched(two, monkeypatch):
    client, calls, _ = two
    import app.services.sync_service as sync_service

    class NoSplits:
        def __init__(self, *a, **k): pass
        def get_activity(self, activity_id):
            calls.append(activity_id)
            return {"id": activity_id, "sport_type": "Run"}

    monkeypatch.setattr(sync_service, "StravaClient", NoSplits)
    assert client.get("/api/activities/10/splits", headers=ADMIN).json() == {"available": True, "splits": []}
    client.get("/api/activities/10/splits", headers=ADMIN)
    assert calls == [10]


def test_strava_trouble_gives_unavailable_and_is_not_cached(two):
    client, calls, state = two
    state["mode"] = "down"
    assert client.get("/api/activities/10/splits", headers=ADMIN).json() == {"available": False, "splits": []}
    state["mode"] = "gone"
    assert client.get("/api/activities/10/splits", headers=ADMIN).json()["available"] is False
    state["mode"] = "ok"
    assert client.get("/api/activities/10/splits", headers=ADMIN).json()["available"] is True


def test_not_connected_gives_unavailable(two, db):
    client, calls, _ = two
    conn = db.get_conn()
    conn.execute("DELETE FROM strava_accounts WHERE user_id = 1")
    conn.commit()
    conn.close()
    assert client.get("/api/activities/10/splits", headers=ADMIN).json() == {"available": False, "splits": []}
    assert calls == []


def test_you_cannot_read_splits_of_someone_elses_run(two):
    client, calls, _ = two
    assert client.get("/api/activities/20/splits", headers=ADMIN).status_code == 404
    assert client.get("/api/activities/999/splits", headers=ADMIN).status_code == 404
    assert calls == []


def test_family_splits_follow_the_sharing_level_and_use_the_owners_strava(two):
    client, calls, _ = two
    url = "/api/family/2/activities/20/splits"
    assert client.get(url, headers=ADMIN).status_code == 403  # private by default
    client.put("/api/me", headers=FAMILY, json={"sharing_level": "overview"})
    assert client.get(url, headers=ADMIN).status_code == 403
    client.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    body = client.get(url, headers=ADMIN).json()
    assert body["available"] is True and len(body["splits"]) == 3
    assert client.get("/api/family/2/activities/10/splits", headers=ADMIN).status_code == 404  # Henrik's run via Anna's id
