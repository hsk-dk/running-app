"""The route poster's data: every route the person has, and only theirs."""
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
