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

def test_a_parent_sees_days_done_and_the_development_with_numbers_for_a_childs_challenge(two):
    two.put("/api/admin/users/2/child", headers=ADMIN, json={"is_child": True})
    today = timeutil.today()
    cid = make(two, name="Planke", unit="sek", start_value=20, start_date=(today - timedelta(days=10)).isoformat()).json()["id"]
    two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 45})
    anna = next(m for m in two.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    first = anna["guardian"]["challenges"][0]
    assert first["name"] == "Planke" and first["unit"] == "sek" and first["done_week"] == 1 and first["streak_days"] == 1
    assert first["first_count"] is None  # one day says nothing about development yet
    for i, n in ((6, 20), (4, 28), (2, 35)):
        two.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": n, "day": (today - timedelta(days=i)).isoformat()})
    anna = next(m for m in two.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    first = anna["guardian"]["challenges"][0]
    assert (first["first_count"], first["recent_best"], first["weeks"]) == (20, 45, 1)


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


# ---- development, improvement milestones and showing off --------------------------------------------------

def _log(client, cid, n, days_ago=0, headers=FAMILY):
    return client.put(f"/api/challenges/{cid}/log", headers=headers, json={"count": n, "day": (timeutil.today() - timedelta(days=days_ago)).isoformat()})


def _started(client, days=20, **over):
    return make(client, start_date=(timeutil.today() - timedelta(days=days)).isoformat(), **over).json()["id"]


def test_the_card_has_a_history_a_development_and_knows_a_new_best(two):
    cid = _started(two)
    for n, ago in ((5, 6), (6, 4), (7, 2), (10, 0)):
        _log(two, cid, n, ago)
    c = two.get("/api/challenges", headers=FAMILY).json()[0]
    assert c["progress"] == {"first_count": 5, "recent_best": 10, "weeks": 1}
    assert c["new_best_today"] is True and c["best_day"] == 10
    assert c["history"][-1]["count"] == 10 and c["history"][-1]["date"] == timeutil.today().isoformat()
    assert len(c["history"]) == 21 and c["history"][0]["target"] is not None
    assert two.get("/api/challenges", headers=ADMIN).json() == []  # still only your own


def test_the_first_logged_day_is_not_a_new_best_and_equal_is_not_better(two):
    cid = _started(two)
    assert _log(two, cid, 8).json()["new_best_today"] is False
    _log(two, cid, 8, 1)
    assert two.get("/api/challenges", headers=FAMILY).json()[0]["new_best_today"] is False  # 8 is not more than 8


def test_the_family_sees_improvement_in_words_only_never_the_numbers(two, db):
    cid = _started(two, name="Armbøjninger")
    for n, ago in ((5, 6), (6, 4), (12, 0)):  # a new best, and more than twice the starting target of 5
        _log(two, cid, n, ago)
    from app.repositories import users as users_repo
    c = db.get_conn(); users_repo.set_sharing_level(c, 2, "overview"); c.commit(); c.close()
    anna = next(m for m in two.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    labels = {x["label"] for x in anna["new_milestones"]}
    assert {"Ny bedste dag: Armbøjninger", "Fordoblet startmålet: Armbøjninger"} <= labels
    assert not any(any(ch.isdigit() for ch in x["label"]) for x in anna["new_milestones"] if "bedste" in x["label"] or "Fordoblet" in x["label"])


# ---- showing off: the person chooses, with the number ------------------------------------------------------

def test_a_reached_goal_can_be_shown_to_the_family_with_the_number_and_taken_back(two):
    cid = _started(two, name="Armbøjninger")
    _log(two, cid, 14)
    r = two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={})
    assert r.status_code == 200 and r.json()["shared_today"] is True
    for viewer in (ADMIN, FAMILY):
        brags = two.get("/api/family", headers=viewer).json()["brags"]
        assert [(b["name"], b["challenge"], b["count"], b["unit"], b["date"]) for b in brags] == [("Anna", "Armbøjninger", 14, "stk", timeutil.today().isoformat())]
    assert two.get("/api/family", headers=ADMIN).json()["brags"][0]["is_me"] is False
    assert two.get("/api/family", headers=FAMILY).json()["brags"][0]["is_me"] is True
    assert two.delete(f"/api/challenges/{cid}/share", headers=FAMILY).json()["shared_today"] is False
    assert two.get("/api/family", headers=ADMIN).json()["brags"] == []


def test_only_a_day_you_did_and_reached_or_beat_can_be_shown_and_never_someone_elses(two):
    cid = _started(two)
    assert two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={}).status_code == 409  # nothing written today
    _log(two, cid, 1)  # far below the target
    assert two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={}).status_code == 409
    _log(two, cid, 9, 3)
    _log(two, cid, 4, 2)
    assert two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={"day": (timeutil.today() - timedelta(days=3)).isoformat()}).status_code == 200
    assert two.put(f"/api/challenges/{cid}/share", headers=ADMIN, json={}).status_code == 404
    assert two.delete(f"/api/challenges/{cid}/share", headers=ADMIN).status_code == 404
    tomorrow = (timeutil.today() + timedelta(days=1)).isoformat()
    assert two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={"day": tomorrow}).status_code == 409


def test_a_new_best_below_the_target_can_be_shown_too(two):
    cid = _started(two, start_value=10, step=0)
    _log(two, cid, 4, 3)  # below the target of 10
    _log(two, cid, 6, 0)  # still below the target, but more than ever
    assert two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={}).status_code == 200


def test_changing_the_number_takes_the_showing_off_back_and_so_does_putting_the_challenge_away(two):
    cid = _started(two)
    _log(two, cid, 14)
    two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={})
    _log(two, cid, 20)  # a different number is not what was shown
    assert two.get("/api/family", headers=ADMIN).json()["brags"] == []
    two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={})
    assert len(two.get("/api/family", headers=ADMIN).json()["brags"]) == 1
    two.delete(f"/api/challenges/{cid}", headers=FAMILY)
    assert two.get("/api/family", headers=ADMIN).json()["brags"] == []


def test_showing_off_reaches_the_family_even_when_the_person_shares_nothing_else(two, db):
    cid = _started(two)
    _log(two, cid, 14)
    two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={})
    assert next(m for m in two.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)["shared"] is False
    assert len(two.get("/api/family", headers=ADMIN).json()["brags"]) == 1  # the person chose this one thing


def test_old_showing_off_fades_after_three_weeks(two, db):
    cid = _started(two, days=30)
    _log(two, cid, 14, 14)
    two.put(f"/api/challenges/{cid}/share", headers=FAMILY, json={"day": (timeutil.today() - timedelta(days=14)).isoformat()})
    assert len(two.get("/api/family", headers=ADMIN).json()["brags"]) == 1
    c = db.get_conn(); c.execute("UPDATE challenge_brags SET day = ?", ((timeutil.today() - timedelta(days=22)).isoformat(),)); c.execute("UPDATE challenge_logs SET day = ?", ((timeutil.today() - timedelta(days=22)).isoformat(),)); c.commit(); c.close()
    assert two.get("/api/family", headers=ADMIN).json()["brags"] == []
