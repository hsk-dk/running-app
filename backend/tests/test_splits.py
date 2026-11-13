"""Kilometre splits: kept per run, and shared only the way runs are. (Where they come from is tested in test_garmin.)"""
import json

import pytest

from tests.auth_helpers import ADMIN, FAMILY
from tests.conftest import add_activity

SPLITS = [{"km": 1, "distance_m": 1000.0, "time_s": 330, "pace_s_per_km": 330.0, "elevation_m": 4.2, "partial": False, "avg_hr": 128}]


@pytest.fixture()
def two(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    add_activity(db, 10, "2026-11-10T08:00:00Z", user_id=1)
    add_activity(db, 20, "2026-11-10T08:00:00Z", user_id=2)
    return proxy, db


def store(db, activity_id, splits=SPLITS):
    c = db.get_conn(); c.execute("UPDATE activities SET splits_json = ? WHERE id = ?", (json.dumps(splits), activity_id)); c.commit(); c.close()


def test_stored_splits_are_served(two):
    client, db = two
    store(db, 10)
    assert client.get("/api/activities/10/splits", headers=ADMIN).json() == {"available": True, "splits": SPLITS}


def test_an_older_run_without_a_garmin_link_has_no_splits_and_nothing_is_fetched(two):
    client, _ = two
    assert client.get("/api/activities/10/splits", headers=ADMIN).json() == {"available": True, "splits": []}


def test_you_cannot_read_splits_of_someone_elses_run(two):
    client, db = two
    store(db, 20)
    assert client.get("/api/activities/20/splits", headers=ADMIN).status_code == 404
    assert client.get("/api/activities/999/splits", headers=ADMIN).status_code == 404


def test_family_splits_follow_the_sharing_level_and_never_carry_heart_rate(two):
    client, db = two
    store(db, 20)
    url = "/api/family/2/activities/20/splits"
    assert client.get(url, headers=ADMIN).status_code == 403  # private by default
    client.put("/api/me", headers=FAMILY, json={"sharing_level": "overview"})
    assert client.get(url, headers=ADMIN).status_code == 403
    client.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    body = client.get(url, headers=ADMIN).json()
    assert body["available"] is True and body["splits"][0]["time_s"] == 330 and body["splits"][0]["avg_hr"] is None
    assert client.get("/api/family/2/activities/10/splits", headers=ADMIN).status_code == 404  # Henrik's run via Anna's id
