"""Children: a parent marks them, they see less, other family sees only milestones, and the parents see a short summary."""
from datetime import timedelta

import pytest

from app.domain import timeutil
from tests.auth_helpers import ADMIN, FAMILY
from tests.conftest import add_activity

ANNA = 2  # a family member (the child, in these tests)
BO = {"x-authentik-uid": "u-bo", "x-authentik-username": "bo", "x-authentik-name": "Bo", "x-authentik-groups": "homelab-family"}
BO_ID = 3


def local(db, id, day, km, minutes, user_id):
    add_activity(db, id, f"{day}T08:00:00Z", distance_m=km * 1000, moving_time_s=minutes * 60, user_id=user_id)
    c = db.get_conn(); c.execute("UPDATE activities SET start_date_local = ? WHERE id = ?", (f"{day}T09:00:00Z", id)); c.commit(); c.close()


def share(db, user_id, level):
    from app.repositories import users as users_repo
    c = db.get_conn(); users_repo.set_sharing_level(c, user_id, level); c.commit(); c.close()


@pytest.fixture()
def home(proxy, db):
    """Henrik (admin, parent, 1), Anna (the child, 2) and Bo (a sibling, 3)."""
    for h in (ADMIN, FAMILY, BO):
        proxy.get("/api/me", headers=h)
    proxy.put(f"/api/admin/users/{ANNA}/child", headers=ADMIN, json={"is_child": True})
    return proxy


def member(client, headers, user_id):
    return next(m for m in client.get("/api/family", headers=headers).json()["members"] if m["user_id"] == user_id)


# ---- marking a child --------------------------------------------------------------------------------------

def test_only_a_parent_can_list_people_and_mark_a_child(proxy, db):
    for h in (ADMIN, FAMILY):
        proxy.get("/api/me", headers=h)
    people = proxy.get("/api/admin/users", headers=ADMIN).json()
    assert [(p["name"], p["is_child"]) for p in people] == [("Henrik", False), ("Anna", False)]
    assert proxy.get("/api/admin/users", headers=FAMILY).status_code == 403
    assert proxy.put(f"/api/admin/users/{ANNA}/child", headers=FAMILY, json={"is_child": True}).status_code == 403
    assert proxy.put(f"/api/admin/users/{ANNA}/child", headers=ADMIN, json={"is_child": True}).json()["is_child"] is True
    assert proxy.get("/api/me", headers=FAMILY).json()["is_child"] is True
    assert proxy.get("/api/me", headers=ADMIN).json()["is_child"] is False


def test_a_parent_cannot_mark_themselves_and_an_unknown_person_is_not_found(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    assert proxy.put("/api/admin/users/1/child", headers=ADMIN, json={"is_child": True}).status_code == 403
    assert proxy.put("/api/admin/users/99/child", headers=ADMIN, json={"is_child": True}).status_code == 404
    assert proxy.put("/api/admin/users/1/child", headers=ADMIN, json={}).status_code == 422


def test_a_child_can_be_unmarked_again(home):
    assert home.put(f"/api/admin/users/{ANNA}/child", headers=ADMIN, json={"is_child": False}).json()["is_child"] is False
    assert home.get("/api/me", headers=FAMILY).json()["is_child"] is False


# ---- what the parents see -----------------------------------------------------------------------------------

def test_a_parent_sees_a_short_summary_of_a_child_even_when_the_child_shares_nothing(home, db):
    today = timeutil.today()
    local(db, 1, today.isoformat(), 3.0, 25, ANNA)
    local(db, 2, today.isoformat(), 2.0, 15, ANNA)  # the same day: two runs, one active day
    local(db, 3, (today - timedelta(days=45)).isoformat(), 4.0, 30, ANNA)  # last month or earlier
    share(db, ANNA, "private")
    m = member(home, ADMIN, ANNA)
    assert m["level"] == "guardian" and m["shared"] is True and m["is_child"] is True
    g = m["guardian"]
    assert g["runs_week"] == 2 and g["active_days_week"] == 1 and g["minutes_week"] == 40
    assert g["runs_month"] == 2 and g["minutes_month"] == 40  # the run 45 days ago is not this month's
    assert g["last_run_date"] == today.isoformat() and g["streak_weeks"] >= 1
    assert m["recent_runs"] is None and m["month_km"] is None  # no runs, no kilometres


def test_the_parents_summary_has_no_distance_pace_heart_rate_or_place(home, db):
    local(db, 1, timeutil.today().isoformat(), 5.0, 30, ANNA)
    g = member(home, ADMIN, ANNA)["guardian"]
    assert set(g) == {"runs_week", "active_days_week", "minutes_week", "runs_month", "minutes_month", "last_run_date", "streak_weeks"}


def test_a_parent_still_cannot_open_a_childs_runs(home, db):
    local(db, 1, timeutil.today().isoformat(), 5.0, 30, ANNA)
    assert home.get(f"/api/family/{ANNA}/activities", headers=ADMIN).status_code == 403
    assert home.get(f"/api/family/{ANNA}/activities/1", headers=ADMIN).status_code == 403


def test_short_runs_do_not_count_in_the_summary(home, db):
    local(db, 1, timeutil.today().isoformat(), 0.6, 4, ANNA)
    g = member(home, ADMIN, ANNA)["guardian"]
    assert g["runs_week"] == 0 and g["last_run_date"] is None


# ---- what everyone else sees ---------------------------------------------------------------------------------

def test_a_sibling_sees_only_a_childs_milestones_and_only_if_the_child_shares(home, db):
    local(db, 1, timeutil.today().isoformat(), 5.5, 40, ANNA)
    share(db, ANNA, "private")
    assert member(home, BO, ANNA)["shared"] is False
    share(db, ANNA, "all")
    m = member(home, BO, ANNA)
    assert m["level"] == "milestones" and m["shared"] is True
    assert {x["label"] for x in m["new_milestones"]} >= {"Første løb", "Første løb på 5 km"}
    assert m["week"] is None and m["month_km"] is None and m["streak_weeks"] is None and m["recent_runs"] is None and m["guardian"] is None
    assert home.get(f"/api/family/{ANNA}/activities", headers=BO).status_code == 403


def test_a_child_sees_other_people_only_as_milestones(home, db):
    local(db, 2, timeutil.today().isoformat(), 10.0, 60, BO_ID)
    share(db, BO_ID, "all")
    m = member(home, FAMILY, BO_ID)  # Anna, the child, looking at Bo
    assert m["level"] == "milestones" and m["recent_runs"] is None and m["month_km"] is None
    assert home.get(f"/api/family/{BO_ID}/activities", headers=FAMILY).status_code == 403
    assert member(home, ADMIN, BO_ID)["level"] == "all"  # an adult sees what Bo shares, as before


def test_a_child_sees_themselves_in_full(home, db):
    local(db, 1, timeutil.today().isoformat(), 5.0, 30, ANNA)
    m = member(home, FAMILY, ANNA)
    assert m["level"] == "all" and m["is_me"] is True and len(m["recent_runs"]) == 1


# ---- the family goal ----------------------------------------------------------------------------------------------

def test_the_goal_counts_everyone_who_shares_together_and_shows_no_one_part(home, db):
    today = timeutil.today().isoformat()
    local(db, 1, today, 10.0, 60, 1)
    local(db, 2, today, 4.0, 30, ANNA)
    local(db, 3, today, 7.0, 40, BO_ID)
    share(db, 1, "overview"); share(db, ANNA, "overview"); share(db, BO_ID, "private")
    body = home.get("/api/family", headers=ADMIN).json()
    assert body["goal"]["km"] == 14.0 and body["total_km_this_month"] == 14.0  # Bo shares nothing, so Bo's 7 km are not in it
    assert body["goal"]["target_km"] is None
    assert set(body["goal"]) == {"target_km", "km", "month"}


def test_only_a_parent_sets_the_goal_and_it_can_be_removed(home, db):
    assert home.put("/api/family/goal", headers=FAMILY, json={"target_km": 100}).status_code == 403
    r = home.put("/api/family/goal", headers=ADMIN, json={"target_km": 100})
    assert r.status_code == 200 and r.json()["target_km"] == 100
    assert home.get("/api/family", headers=FAMILY).json()["goal"]["target_km"] == 100
    assert home.put("/api/family/goal", headers=ADMIN, json={"target_km": 0}).status_code == 422
    assert home.put("/api/family/goal", headers=ADMIN, json={"target_km": 99999}).status_code == 422
    assert home.put("/api/family/goal", headers=ADMIN, json={"target_km": None}).json()["target_km"] is None
    assert home.get("/api/family", headers=ADMIN).json()["goal"]["target_km"] is None


def test_the_schema_has_the_child_flag_with_adults_as_the_default(proxy, db):
    c = db.get_conn()
    cols = {r["name"]: r for r in c.execute("PRAGMA table_info(users)").fetchall()}
    c.close()
    assert "is_child" in cols and cols["is_child"]["dflt_value"] == "0"
