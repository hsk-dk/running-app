"""Daily challenges through the app: always your own, calm rules, and parents see days done, not numbers."""
from datetime import timedelta

import pytest

from app.domain import timeutil
from tests.auth_helpers import ADMIN, FAMILY

PLAN = {"name": "Armbøjninger", "unit": "stk", "start_value": 5, "step": 1, "step_every_days": 7, "rest_weekdays": []}


@pytest.fixture()
def two(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    return proxy


def make(client, headers=FAMILY, **over):
    return client.post("/api/challenges", headers=headers, json={**PLAN, **over})


def test_a_challenge_is_created_with_todays_target_and_nothing_done(two):
    r = make(two)
    assert r.status_code == 201
    c = r.json()
    assert (c["name"], c["unit"], c["today_target"], c["today_count"], c["today_done"]) == ("Armbøjninger", "stk", 5, None, False)
    assert c["streak_days"] == 0 and c["plan"]["start_value"] == 5 and c["plan"]["start_date"] == timeutil.today().isoformat()
    assert len(c["week"]) == 7 and sum(1 for d in c["week"] if d["status"] == "today") == 1
    assert [x["id"] for x in two.get("/api/challenges", headers=FAMILY).json()] == [c["id"]]


def test_logging_todays_count_marks_the_day_and_keeps_the_best(two):
    cid = make(two).json()["id"]
    c = two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 7}).json()
    assert c["today_done"] is True and c["today_count"] == 7 and c["best_day"] == 7 and c["total"] == 7 and c["streak_days"] == 1
    c = two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 3}).json()  # a rewrite of today, not an addition
    assert c["today_count"] == 3 and c["today_done"] is False and c["total"] == 3
    c = two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 0}).json()  # 0 clears the day
    assert c["today_count"] is None and c["total"] == 0


def test_you_can_write_yesterday_but_not_tomorrow_or_last_month(two):
    cid = make(two, start_date=(timeutil.today() - timedelta(days=30)).isoformat()).json()["id"]
    today = timeutil.today()
    ok = two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 9, "day": (today - timedelta(days=1)).isoformat()})
    assert ok.status_code == 200 and ok.json()["best_day"] == 9
    assert two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 9, "day": (today + timedelta(days=1)).isoformat()}).status_code == 409
    assert two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 9, "day": (today - timedelta(days=15)).isoformat()}).status_code == 409
    assert two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 9, "day": (today - timedelta(days=14)).isoformat()}).status_code == 200


def test_the_plan_is_validated(two):
    for bad in ({"name": ""}, {"name": "x" * 41}, {"start_value": 0}, {"start_value": 10001}, {"step": -1}, {"step_every_days": 0},
                {"unit": "km"}, {"rest_weekdays": [7]}, {"rest_weekdays": [0, 1, 2, 3, 4, 5, 6]}, {"cap": 0}):
        assert make(two, **bad).status_code == 422, bad
    assert two.put("/api/challenges/1/log", headers=FAMILY, json={"count": -1}).status_code == 422
    assert make(two, rest_weekdays=[5, 6], cap=20, step=0).status_code == 201


def test_the_plan_can_be_changed_and_the_challenge_put_away(two):
    cid = make(two).json()["id"]
    c = two.put(f"/api/challenges/{cid}", headers=FAMILY, json={**PLAN, "start_value": 8, "step": 2}).json()
    assert c["today_target"] == 8 and c["plan"]["step"] == 2
    assert two.delete(f"/api/challenges/{cid}", headers=FAMILY).status_code == 204
    assert two.get("/api/challenges", headers=FAMILY).json() == []
    assert two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 5}).status_code == 404
    assert two.put(f"/api/challenges/{cid}", headers=FAMILY, json=PLAN).status_code == 404


def test_nobody_else_can_read_change_log_or_delete_your_challenge(two):
    cid = make(two).json()["id"]
    assert two.get("/api/challenges", headers=ADMIN).json() == []
    assert two.put(f"/api/challenges/{cid}/log", headers=ADMIN, json={"count": 5}).status_code == 404
    assert two.put(f"/api/challenges/{cid}", headers=ADMIN, json=PLAN).status_code == 404
    assert two.delete(f"/api/challenges/{cid}", headers=ADMIN).status_code == 404
    assert two.get("/api/challenges", headers=FAMILY).json()[0]["total"] == 0


def test_at_most_ten_at_a_time(two):
    for i in range(10):
        assert make(two, name=f"Ud {i}").status_code == 201
    assert make(two, name="Én for meget").status_code == 409
    two.delete("/api/challenges/1", headers=FAMILY)
    assert make(two, name="Nu er der plads").status_code == 201


def test_a_rest_day_has_no_target_and_a_future_start_is_not_started(two):
    today = timeutil.today()
    c = make(two, rest_weekdays=[today.weekday()]).json()
    assert c["today_target"] is None and c["rest_today"] is True
    later = make(two, start_date=(today + timedelta(days=3)).isoformat()).json()
    assert later["not_started"] is True and later["today_target"] is None


# ---- what the parents and the family see ------------------------------------------------------------

def test_a_parent_sees_days_done_for_a_childs_challenge_and_never_the_counts(two):
    two.put(f"/api/admin/users/2/child", headers=ADMIN, json={"is_child": True})
    cid = make(two, name="Planke", unit="sek", start_value=20).json()["id"]
    two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 45})
    anna = next(m for m in two.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    items = anna["guardian"]["challenges"]
    assert items == [{"name": "Planke", "done_week": 1, "planned_week": items[0]["planned_week"], "streak_days": 1}]
    assert "45" not in str(anna) and "best_day" not in str(anna) and "total" not in str(anna)


def test_a_seven_day_run_shows_up_as_a_milestone_for_the_family(two, db):
    today = timeutil.today()
    cid = make(two, start_date=(today - timedelta(days=6)).isoformat()).json()["id"]
    for i in range(7):
        two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 6, "day": (today - timedelta(days=i)).isoformat()})
    from app.repositories import users as users_repo
    c = db.get_conn(); users_repo.set_sharing_level(c, 2, "overview"); c.commit(); c.close()
    anna = next(m for m in two.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    assert "7 dage i træk: Armbøjninger" in {x["label"] for x in anna["new_milestones"]}


def test_a_private_person_shares_no_challenge_milestones(two, db):
    today = timeutil.today()
    cid = make(two, start_date=(today - timedelta(days=6)).isoformat()).json()["id"]
    for i in range(7):
        two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 6, "day": (today - timedelta(days=i)).isoformat()})
    anna = next(m for m in two.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    assert anna["shared"] is False and anna["new_milestones"] is None


def test_the_tables_exist_after_migration(proxy, db):
    c = db.get_conn()
    names = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    version = c.execute("PRAGMA user_version").fetchone()[0]
    c.close()
    assert {"challenges", "challenge_logs"} <= names and version >= 14
