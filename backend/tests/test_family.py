"""What family members can see of each other. Private until a person chooses otherwise."""
from datetime import timedelta

import pytest

from app.domain import timeutil
from tests.auth_helpers import ADMIN, FAMILY, patch_settings
from tests.conftest import add_activity, add_plan, connect_strava

ANNA = 2  # the second user to sign in


@pytest.fixture()
def family(proxy, db):
    """Henrik (admin, user 1) and Anna (user 2), both connected to Strava, with a run each this week."""
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    connect_strava(db, user_id=1, athlete_id="11")
    connect_strava(db, user_id=ANNA, athlete_id="22")

    today = timeutil.today()
    monday = today - timedelta(days=today.weekday())
    last_week = monday - timedelta(days=4)
    add_activity(db, 1, f"{monday.isoformat()}T08:00:00Z", distance_m=10000, moving_time_s=3000, name="Henriks løb", user_id=1)
    add_activity(db, 2, f"{monday.isoformat()}T08:00:00Z", distance_m=5000, moving_time_s=1800, name="Annas løb", user_id=ANNA,
                 raw={"map": {"summary_polyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"}})
    add_activity(db, 3, f"{last_week.isoformat()}T08:00:00Z", distance_m=4000, moving_time_s=1500, name="Annas løb før", user_id=ANNA)
    add_plan(db, monday.isoformat(), status="gennemført", user_id=ANNA)
    add_plan(db, (monday + timedelta(days=6)).isoformat(), status="planlagt", user_id=ANNA)
    add_plan(db, (monday + timedelta(days=2)).isoformat(), status="gennemført", mandatory=0, user_id=ANNA)  # optional: not counted
    return proxy


def _anna(client, headers=ADMIN):
    members = client.get("/api/family", headers=headers).json()["members"]
    return next(m for m in members if m["user_id"] == ANNA)


def test_a_person_who_has_not_shared_shows_only_their_name(family):
    anna = _anna(family)
    assert (anna["name"], anna["level"], anna["shared"]) == ("Anna", "private", False)
    assert (anna["week"], anna["month_km"], anna["streak_weeks"], anna["recent_runs"]) == (None, None, None, None)


def test_overview_shares_numbers_but_not_the_runs(family):
    family.put("/api/me", headers=FAMILY, json={"sharing_level": "overview"})
    anna = _anna(family)
    assert anna["shared"] is True and anna["level"] == "overview"
    assert anna["week"] == {"done": 1, "total": 2, "open": 1}  # the optional run is not counted
    assert anna["month_km"] >= 5 and anna["streak_weeks"] == 2
    assert anna["recent_runs"] is None
    assert family.get(f"/api/family/{ANNA}/activities", headers=ADMIN).status_code == 403
    assert family.get(f"/api/family/{ANNA}/activities/2", headers=ADMIN).status_code == 403


def test_all_shares_recent_runs_without_heart_rate_and_the_route(family):
    family.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    anna = _anna(family)
    assert anna["level"] == "all"
    assert {r["name"] for r in anna["recent_runs"]} == {"Annas løb", "Annas løb før"}
    assert set(anna["recent_runs"][0]) == {"id", "date", "name", "distance_km", "duration_min"}

    runs = family.get(f"/api/family/{ANNA}/activities", headers=ADMIN).json()
    assert {r["id"] for r in runs} == {2, 3}
    assert all("avg_hr" not in r and "matched_planned_run_id" not in r for r in runs)
    detail = family.get(f"/api/family/{ANNA}/activities/2", headers=ADMIN).json()
    assert detail["route"] is not None and detail["name"] == "Annas løb"
    assert not {"avg_hr", "max_hr", "matched_planned_run_id", "is_extra"} & set(detail)


def test_you_always_see_all_of_yourself(family):
    me = family.get("/api/family", headers=FAMILY).json()["members"][0]
    assert (me["is_me"], me["level"], me["shared"]) == (True, "all", True)
    assert me["recent_runs"] and me["week"]["total"] == 2


def test_you_come_first_then_the_others_by_name(family):
    names = [m["name"] for m in family.get("/api/family", headers=FAMILY).json()["members"]]
    assert names == ["Anna", "Henrik"]
    names = [m["name"] for m in family.get("/api/family", headers=ADMIN).json()["members"]]
    assert names == ["Henrik", "Anna"]


def test_the_family_total_only_counts_what_is_shared(family):
    own = family.get("/api/family", headers=ADMIN).json()["total_km_this_month"]
    family.put("/api/me", headers=FAMILY, json={"sharing_level": "overview"})
    with_anna = family.get("/api/family", headers=ADMIN).json()["total_km_this_month"]
    assert with_anna > own
    assert with_anna == pytest.approx(own + _anna(family)["month_km"], abs=0.1)


def test_switching_family_sharing_off_hides_everyone_else(family, monkeypatch):
    family.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    patch_settings(monkeypatch, FAMILY_SHARING_ENABLED=False)
    body = family.get("/api/family", headers=ADMIN).json()
    assert body["sharing_enabled"] is False
    assert _anna(family)["shared"] is False
    assert family.get(f"/api/family/{ANNA}/activities", headers=ADMIN).status_code == 403
    assert body["members"][0]["recent_runs"]  # you still see yourself


def test_someone_without_strava_is_shared_but_has_no_numbers(family, db):
    family.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM strava_accounts WHERE user_id = ?", (ANNA,))
        conn.commit()
    finally:
        conn.close()
    anna = _anna(family)
    assert (anna["shared"], anna["strava_connected"], anna["week"], anna["recent_runs"]) == (True, False, None, None)


def test_unknown_member_and_someone_elses_activity_id(family):
    family.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    assert family.get("/api/family/999/activities", headers=ADMIN).status_code == 404
    assert family.get(f"/api/family/{ANNA}/activities/1", headers=ADMIN).status_code == 404  # run 1 is Henrik's, not Anna's


def test_your_own_runs_are_reachable_through_the_family_route_even_when_private(family):
    assert family.get("/api/family/1/activities", headers=ADMIN).status_code == 200


def test_outsiders_never_reach_the_family_pages(family):
    from tests.auth_helpers import OUTSIDER

    assert family.get("/api/family", headers=OUTSIDER).status_code == 403
