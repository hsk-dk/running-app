"""The route poster's data: every route the person has, and only theirs."""
import json

from tests.auth_helpers import ADMIN, FAMILY
from tests.conftest import add_activity

LINE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


def test_routes_lists_runs_with_a_route_newest_first_and_skips_the_rest(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    add_activity(db, 1, "2026-11-01T08:00:00Z", distance_m=5000, raw={"map": {"summary_polyline": LINE}})
    add_activity(db, 2, "2026-11-05T08:00:00Z", distance_m=8000, raw={"map": {"summary_polyline": LINE}})
    add_activity(db, 3, "2026-11-06T08:00:00Z", raw={"map": {"summary_polyline": None}})  # treadmill
    add_activity(db, 4, "2026-11-07T08:00:00Z", raw={})  # no map at all (e.g. a Smashrun run)
    add_activity(db, 5, "2026-11-08T08:00:00Z", sport_type="Ride", raw={"map": {"summary_polyline": LINE}})
    r = proxy.get("/api/activities/routes", headers=ADMIN)
    assert r.status_code == 200
    assert [(x["id"], x["distance_km"], x["date"]) for x in r.json()] == [(2, 8.0, "2026-11-05"), (1, 5.0, "2026-11-01")]
    assert r.json()[0]["route"] == LINE


def test_routes_are_only_the_signed_in_persons_own(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    add_activity(db, 1, "2026-11-01T08:00:00Z", raw={"map": {"summary_polyline": LINE}}, user_id=1)
    add_activity(db, 2, "2026-11-02T08:00:00Z", raw={"map": {"summary_polyline": LINE}}, user_id=2)
    assert [x["id"] for x in proxy.get("/api/activities/routes", headers=ADMIN).json()] == [1]
    assert [x["id"] for x in proxy.get("/api/activities/routes", headers=FAMILY).json()] == [2]


def test_the_limit_caps_the_answer_and_routes_is_not_mistaken_for_an_activity_id(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    for i in range(1, 6):
        add_activity(db, i, f"2026-11-0{i}T08:00:00Z", raw={"map": {"summary_polyline": LINE}})
    assert len(proxy.get("/api/activities/routes?limit=3", headers=ADMIN).json()) == 3
    assert proxy.get("/api/activities/routes?limit=0", headers=ADMIN).status_code == 422


def test_routes_carry_the_runs_name_and_duration_for_the_labels(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    add_activity(db, 1, "2026-11-01T08:00:00Z", distance_m=5000, moving_time_s=1800, name="Horsens - W7 Easy", raw={"map": {"summary_polyline": LINE}})
    [r] = proxy.get("/api/activities/routes", headers=ADMIN).json()
    assert (r["name"], r["duration_min"], r["distance_km"]) == ("Horsens - W7 Easy", 30.0, 5.0)


PROFILE = {"t": [0, 10, 20], "d": [0.0, 28.0, 56.0], "hr": [120, 130, 140], "v": [2.8, 2.8, 2.8], "cad": None, "alt": None}


def store_profile(db, activity_id, profile=PROFILE):
    c = db.get_conn(); c.execute("UPDATE activities SET profile_json = ?, fit_status = 'ok' WHERE id = ?", (json.dumps(profile), activity_id)); c.commit(); c.close()


def test_profiles_lists_runs_that_have_one_newest_first_with_heart_rate_and_only_the_persons_own(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    add_activity(db, 1, "2026-11-01T08:00:00Z", distance_m=5000, moving_time_s=1800, name="Old", user_id=1)
    add_activity(db, 2, "2026-11-05T08:00:00Z", distance_m=6000, moving_time_s=2000, name="New", user_id=1)
    add_activity(db, 3, "2026-11-06T08:00:00Z", name="No profile", user_id=1)
    add_activity(db, 4, "2026-11-07T08:00:00Z", name="Someone else's", user_id=2)
    for rid in (1, 2, 4):
        store_profile(db, rid)
    r = proxy.get("/api/activities/profiles", headers=ADMIN)
    assert r.status_code == 200
    assert [x["name"] for x in r.json()] == ["New", "Old"]
    assert r.json()[0]["profile"]["hr"] == [120, 130, 140] and r.json()[0]["duration_min"] == 33.3
    assert [x["name"] for x in proxy.get("/api/activities/profiles", headers=FAMILY).json()] == ["Someone else's"]
    assert len(proxy.get("/api/activities/profiles?limit=1", headers=ADMIN).json()) == 1
    assert proxy.get("/api/activities/profiles?limit=0", headers=ADMIN).status_code == 422


def test_a_run_with_a_damaged_stored_profile_is_left_out_not_a_crash(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    add_activity(db, 1, "2026-11-01T08:00:00Z", user_id=1)
    c = db.get_conn(); c.execute("UPDATE activities SET profile_json = 'not json' WHERE id = 1"); c.commit(); c.close()
    assert proxy.get("/api/activities/profiles", headers=ADMIN).json() == []


def test_indoor_lists_runs_without_a_route_newest_first_and_never_a_run_that_has_one(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    add_activity(db, 1, "2026-11-01T08:00:00Z", distance_m=5000, moving_time_s=1800, name="Outdoors", raw={"map": {"summary_polyline": LINE}})
    add_activity(db, 2, "2026-11-05T08:00:00Z", distance_m=8000, moving_time_s=2700, name="Løbebånd", raw={"map": {"summary_polyline": None}})
    add_activity(db, 3, "2026-11-06T08:00:00Z", distance_m=6000, moving_time_s=2100, name="No map", raw={})
    add_activity(db, 4, "2026-11-08T08:00:00Z", sport_type="Ride", raw={})
    r = proxy.get("/api/activities/indoor", headers=ADMIN)
    assert r.status_code == 200
    assert [(x["id"], x["name"], x["distance_km"], x["duration_min"], x["date"]) for x in r.json()] == [
        (3, "No map", 6.0, 35.0, "2026-11-06"),
        (2, "Løbebånd", 8.0, 45.0, "2026-11-05"),
    ]
    # between them, routes and indoor cover every run exactly once
    ids = {x["id"] for x in proxy.get("/api/activities/routes", headers=ADMIN).json()} | {x["id"] for x in r.json()}
    assert ids == {1, 2, 3}


def test_indoor_is_only_the_signed_in_persons_own_and_validates_the_limit(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    add_activity(db, 1, "2026-11-01T08:00:00Z", user_id=1)
    add_activity(db, 2, "2026-11-02T08:00:00Z", user_id=2)
    assert [x["id"] for x in proxy.get("/api/activities/indoor", headers=ADMIN).json()] == [1]
    assert [x["id"] for x in proxy.get("/api/activities/indoor", headers=FAMILY).json()] == [2]
    assert len(proxy.get("/api/activities/indoor?limit=1", headers=ADMIN).json()) == 1
    assert proxy.get("/api/activities/indoor?limit=0", headers=ADMIN).status_code == 422
