"""Stars, the shelf of badges and the family's reward, through the app."""
from datetime import timedelta

import pytest

from app.domain import timeutil
from tests.auth_helpers import ADMIN, FAMILY
from tests.conftest import add_activity

BO = {"x-authentik-uid": "u-bo", "x-authentik-username": "bo", "x-authentik-name": "Bo", "x-authentik-groups": "homelab-family"}


def local(db, id, day, minutes, km=3.0, user_id=1):
    add_activity(db, id, f"{day}T08:00:00Z", distance_m=km * 1000, moving_time_s=minutes * 60, user_id=user_id)
    c = db.get_conn(); c.execute("UPDATE activities SET start_date_local = ? WHERE id = ?", (f"{day}T09:00:00Z", id)); c.commit(); c.close()


def share(db, user_id, level="overview"):
    from app.repositories import users as users_repo
    c = db.get_conn(); users_repo.set_sharing_level(c, user_id, level); c.commit(); c.close()


@pytest.fixture()
def home(proxy, db):
    """Henrik (admin, 1), Anna (2) and Bo (3). Everyone shares an overview."""
    for h in (ADMIN, FAMILY, BO):
        proxy.get("/api/me", headers=h)
    for uid in (1, 2, 3):
        share(db, uid)
    return proxy


def _written_on_the_day(db):
    c = db.get_conn(); c.execute("UPDATE challenge_logs SET logged_on = day"); c.commit(); c.close()


def stars(client, headers=ADMIN):
    return client.get("/api/stars", headers=headers).json()


# ---- stars -------------------------------------------------------------------------------------------------------------

def test_an_active_day_gives_a_star_and_a_short_one_does_not(home, db):
    today = timeutil.today()
    local(db, 1, today.isoformat(), 20)
    local(db, 2, (today - timedelta(days=1)).isoformat(), 10)
    s = stars(home)
    assert s["total"] == 1 and s["week"]["cap"] == 5 and len(s["week"]["days"]) == 7


def test_the_minutes_of_a_day_add_up_across_activities_and_across_kinds(home, db):
    today = timeutil.today().isoformat()
    local(db, 1, today, 8)
    add_activity(db, 2, f"{today}T15:00:00Z", distance_m=0, moving_time_s=8 * 60, sport_type="Walk")  # a walk counts too
    assert stars(home)["total"] == 1


def test_a_challenge_day_gives_a_star_on_top_of_an_active_day(home, db):
    today = timeutil.today()
    cid = home.post("/api/challenges", headers=ADMIN, json={"name": "Armbøjninger", "unit": "stk", "start_value": 5, "step": 1, "step_every_days": 7, "rest_weekdays": []}).json()["id"]
    home.put(f"/api/challenges/{cid}/log", headers=ADMIN, json={"count": 6})
    assert stars(home)["total"] == 1
    local(db, 1, today.isoformat(), 20)
    assert stars(home)["total"] == 2


def test_at_most_five_stars_a_week_are_earned(home, db):
    today = timeutil.today()
    monday = today - timedelta(days=today.weekday())
    for i in range(7):
        day = monday + timedelta(days=i)
        if day <= today:
            local(db, 10 + i, day.isoformat(), 30)
    s = stars(home)
    assert s["week"]["earned"] <= 5 and s["total"] <= 5


def test_only_a_parent_gives_bonus_stars_at_most_three_a_day_and_they_are_not_capped_by_the_week(home, db):
    assert home.post("/api/family/2/bonus", headers=FAMILY, json={}).status_code == 403
    assert home.post("/api/family/99/bonus", headers=ADMIN, json={}).status_code == 404
    for _ in range(3):
        r = home.post("/api/family/2/bonus", headers=ADMIN, json={"note": "Hjalp til"})
        assert r.status_code == 200
    assert home.post("/api/family/2/bonus", headers=ADMIN, json={}).status_code == 409
    assert stars(home, FAMILY)["week"]["bonus"] == 3 and stars(home, FAMILY)["total"] == 3
    assert home.post("/api/family/2/bonus", headers=ADMIN, json={"note": "x" * 81}).status_code == 422


def test_your_stars_are_your_own(home, db):
    local(db, 1, timeutil.today().isoformat(), 30, user_id=2)
    assert stars(home, FAMILY)["total"] == 1
    assert stars(home, ADMIN)["total"] == 0


# ---- the family's reward -----------------------------------------------------------------------------------------------

def test_a_parent_sets_a_reward_and_everyone_who_shares_adds_to_it(home, db):
    assert home.put("/api/family/reward", headers=FAMILY, json={"name": "Biograftur", "cost": 4}).status_code == 403
    r = home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 4, "counts": "all"}).json()
    assert (r["name"], r["cost"], r["stars"], r["reached"], r["remaining"]) == ("Biograftur", 4, 0, False, 4)
    today = timeutil.today().isoformat()
    local(db, 1, today, 30, user_id=1)
    local(db, 2, today, 30, user_id=2)
    got = stars(home, BO)["reward"]
    assert got["stars"] == 2 and got["remaining"] == 2
    assert set(got) == {"id", "name", "cost", "stars", "reached", "remaining", "recent", "counts", "people", "per_week", "estimated", "weeks_left"}  # no one's own part
    assert home.get("/api/family", headers=FAMILY).json()["reward"]["stars"] == 2


def test_someone_who_shares_nothing_does_not_add_but_a_child_always_does(home, db):
    home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 10})
    today = timeutil.today().isoformat()
    share(db, 2, "private")
    local(db, 1, today, 30, user_id=2)
    assert stars(home)["reward"]["stars"] == 0  # private: not in
    home.put("/api/admin/users/2/child", headers=ADMIN, json={"is_child": True})
    assert stars(home)["reward"]["stars"] == 1  # a child counts


def test_stars_from_before_the_reward_was_set_do_not_count(home, db):
    local(db, 1, (timeutil.today() - timedelta(days=1)).isoformat(), 30)
    home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 3})
    assert stars(home)["reward"]["stars"] == 0
    local(db, 2, timeutil.today().isoformat(), 30)
    assert stars(home)["reward"]["stars"] == 1


def test_a_reward_is_reached_then_redeemed_by_a_parent_and_the_next_one_starts_tomorrow_with_what_is_left(home, db):
    home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 3})
    assert home.post("/api/family/reward/redeem", headers=ADMIN).status_code == 409  # not yet
    for _ in range(3):
        home.post("/api/family/2/bonus", headers=ADMIN, json={})
    home.post("/api/family/3/bonus", headers=ADMIN, json={})  # 4 stars for a cost of 3
    assert stars(home)["reward"]["reached"] is True
    assert home.post("/api/family/reward/redeem", headers=FAMILY).status_code == 403
    nxt = home.post("/api/family/reward/redeem", headers=ADMIN).json()
    assert nxt["name"] == "Biograftur" and nxt["stars"] == 1 and nxt["reached"] is False  # one star carried over
    assert nxt["recent"][0]["name"] == "Biograftur" and nxt["recent"][0]["cost"] == 3
    assert home.post("/api/family/reward/redeem", headers=ADMIN).status_code == 409


def test_a_reward_can_be_changed_and_taken_away(home):
    home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 40})
    r = home.put("/api/family/reward", headers=ADMIN, json={"name": "Pizza", "cost": 25}).json()
    assert (r["name"], r["cost"]) == ("Pizza", 25)
    assert home.delete("/api/family/reward", headers=FAMILY).status_code == 403
    assert home.delete("/api/family/reward", headers=ADMIN).status_code == 204
    assert stars(home)["reward"] is None
    assert home.post("/api/family/reward/redeem", headers=ADMIN).status_code == 404
    for bad in ({"name": "", "cost": 5}, {"name": "x", "cost": 0}, {"name": "x", "cost": 1001}, {"name": "x" * 41, "cost": 5}):
        assert home.put("/api/family/reward", headers=ADMIN, json=bad).status_code == 422


def test_a_parent_sees_a_childs_stars_this_week_in_the_parents_summary(home, db):
    home.put("/api/admin/users/2/child", headers=ADMIN, json={"is_child": True})
    home.post("/api/family/2/bonus", headers=ADMIN, json={})
    local(db, 1, timeutil.today().isoformat(), 30, user_id=2)
    anna = next(m for m in home.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    assert anna["guardian"]["stars_week"] == 2


# ---- the shelf of badges --------------------------------------------------------------------------------------------------

def test_the_shelf_has_what_you_earned_and_what_is_ahead_and_is_only_yours(home, db):
    local(db, 1, timeutil.today().isoformat(), 30, km=5.2, user_id=2)
    s = home.get("/api/badges", headers=FAMILY).json()
    got = {b["key"] for b in s["earned"]}
    assert {"first_run", "km_3", "km_5", "stars_1"} <= got
    assert "km_10" in {b["key"] for b in s["ahead"]} and s["total"] == len(s["earned"]) + len(s["ahead"])
    assert all(b["is_new"] for b in s["earned"] if b["key"] in ("first_run", "km_5"))
    other = home.get("/api/badges", headers=ADMIN).json()
    assert other["earned"] == [] and len(other["ahead"]) == s["total"]


def test_challenge_badges_appear_on_the_shelf(home, db):
    today = timeutil.today()
    cid = home.post("/api/challenges", headers=FAMILY, json={"name": "Planke", "unit": "sek", "start_value": 20, "step": 0, "step_every_days": 7, "rest_weekdays": [],
                                                             "start_date": (today - timedelta(days=6)).isoformat()}).json()["id"]
    for i in range(7):
        home.put(f"/api/challenges/{cid}/log", headers=FAMILY, json={"count": 26 - i, "day": (today - timedelta(days=i)).isoformat()})
    _written_on_the_day(db)  # as if each number had been written that very day
    got = {b["key"] for b in home.get("/api/badges", headers=FAMILY).json()["earned"]}
    assert {"challenge_7", "challenge_best"} <= got


def test_the_tables_exist(proxy, db):
    c = db.get_conn()
    names = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    v = c.execute("PRAGMA user_version").fetchone()[0]
    c.close()
    assert {"star_bonus", "family_rewards"} <= names and v >= 16


# ---- the balance between how easy a star is and how often there is a reward -----------------------------------------

def test_a_new_family_gets_a_guess_of_three_stars_a_week_a_person(home):
    r = home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 36}).json()
    assert r["people"] == 3 and r["estimated"] is True and r["per_week"] == 9.0
    assert r["weeks_left"] == 4.0  # 36 left at 9 a week


def test_the_pace_follows_what_the_family_really_earned_the_last_four_weeks(home, db):
    today = timeutil.today()
    for i in range(10):  # ten active days spread over the last weeks: ten stars for one person
        local(db, 100 + i, (today - timedelta(days=i * 2)).isoformat(), 30)
    r = home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 20}).json()
    assert r["estimated"] is False
    assert 2.0 <= r["per_week"] <= 2.6  # about 10 stars in 4 weeks
    assert r["weeks_left"] == round(r["remaining"] / r["per_week"], 1)


def test_weeks_left_is_zero_when_the_reward_is_reached(home):
    home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 2})
    home.post("/api/family/2/bonus", headers=ADMIN, json={})
    home.post("/api/family/2/bonus", headers=ADMIN, json={})
    r = stars(home)["reward"]
    assert r["reached"] is True and r["weeks_left"] == 0.0


def test_stars_from_before_the_last_four_weeks_do_not_change_the_pace(home, db):
    today = timeutil.today()
    for i in range(6):
        local(db, 300 + i, (today - timedelta(days=i * 3)).isoformat(), 30)  # six stars in the window
    before = home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 30}).json()["per_week"]
    for i in range(10):
        local(db, 400 + i, (today - timedelta(days=40 + i * 2)).isoformat(), 30)  # ten more, long ago
    assert stars(home)["reward"]["per_week"] == before and before == 1.5  # six stars in four weeks


def test_the_family_page_has_the_pace_before_any_reward_is_set(home, db):
    body = home.get("/api/family", headers=ADMIN).json()
    assert body["reward"] is None
    assert body["pace"] == {"people": 3, "per_week": 9.0, "estimated": True}  # nothing to measure yet: a guess
    today = timeutil.today()
    for i in range(8):
        local(db, 500 + i, (today - timedelta(days=i * 3)).isoformat(), 30)
    pace = home.get("/api/family", headers=FAMILY).json()["pace"]
    assert pace["estimated"] is False and pace["per_week"] == 2.0 and pace["people"] == 3  # eight stars in four weeks


# ---- fair stars: whose count, and numbers written long afterwards ---------------------------------------------------------

def _challenge(client, headers=FAMILY, days=10, **over):
    body = {"name": "Armbøjninger", "unit": "stk", "start_value": 5, "step": 0, "step_every_days": 7, "rest_weekdays": [],
            "start_date": (timeutil.today() - timedelta(days=days)).isoformat(), **over}
    return client.post("/api/challenges", headers=headers, json=body).json()["id"]


def _write(client, cid, n, ago=0, headers=FAMILY):
    return client.put(f"/api/challenges/{cid}/log", headers=headers, json={"count": n, "day": (timeutil.today() - timedelta(days=ago)).isoformat()})


def test_a_challenge_day_written_today_or_yesterday_earns_a_star_but_one_written_days_later_does_not(home, db):
    cid = _challenge(home)
    _write(home, cid, 6, 0)
    assert stars(home, FAMILY)["total"] == 1
    _write(home, cid, 6, 1)  # written today for yesterday: still in time
    assert stars(home, FAMILY)["total"] == 2
    _write(home, cid, 6, 5)  # five days late
    assert stars(home, FAMILY)["total"] == 2
    own = home.get("/api/challenges", headers=FAMILY).json()[0]
    assert own["total"] == 18 and own["best_day"] == 6  # the person's own card still shows everything honestly


def test_correcting_an_old_day_later_takes_its_star_away_but_a_correction_the_same_day_does_not(home, db):
    cid = _challenge(home)
    _write(home, cid, 6, 0)
    _write(home, cid, 8, 0)  # same day: still fine
    assert stars(home, FAMILY)["total"] == 1
    c = db.get_conn(); c.execute("UPDATE challenge_logs SET logged_on = ?", ((timeutil.today() - timedelta(days=3)).isoformat(),)); c.commit(); c.close()
    # as if the number had been written three days ago for today... then rewritten now is the normal case; here a day long past is rewritten
    _write(home, cid, 7, 4)
    assert stars(home, FAMILY)["total"] == 1  # the day four days ago earned nothing, today's star stays


def test_numbers_written_long_afterwards_earn_no_badge_and_no_family_milestone(home, db):
    today = timeutil.today()
    cid = _challenge(home, days=6, step=0, start_value=20)
    for i in range(7):
        _write(home, cid, 20, i)  # a whole week filled in today
    got = {b["key"] for b in home.get("/api/badges", headers=FAMILY).json()["earned"]}
    assert "challenge_7" not in got and "challenge_best" not in got
    from app.repositories import users as users_repo
    c = db.get_conn(); users_repo.set_sharing_level(c, 2, "overview"); c.commit(); c.close()
    anna = next(m for m in home.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)
    assert not any("dage i træk" in x["label"] for x in anna["new_milestones"])
    assert today  # silence the linter: the date is used by the helper


def test_by_default_only_the_childrens_stars_fill_the_reward(home, db):
    home.put("/api/admin/users/2/child", headers=ADMIN, json={"is_child": True})
    today = timeutil.today().isoformat()
    r = home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 10}).json()
    assert r["counts"] == "children" and r["people"] == 1
    local(db, 1, today, 30, user_id=1)  # a parent runs
    local(db, 2, today, 30, user_id=3)  # a grown-up who is not a child
    assert stars(home)["reward"]["stars"] == 0  # none of that fills the bar
    local(db, 3, today, 30, user_id=2)  # the child
    assert stars(home)["reward"]["stars"] == 1


def test_a_parent_can_let_everyone_count_and_the_choice_is_kept_when_the_reward_is_given(home, db):
    home.put("/api/admin/users/2/child", headers=ADMIN, json={"is_child": True})
    r = home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 2, "counts": "all"}).json()
    assert r["counts"] == "all" and r["people"] == 3
    local(db, 1, timeutil.today().isoformat(), 30, user_id=1)
    local(db, 2, timeutil.today().isoformat(), 30, user_id=3)
    assert stars(home)["reward"]["reached"] is True
    nxt = home.post("/api/family/reward/redeem", headers=ADMIN).json()
    assert nxt["counts"] == "all" and nxt["people"] == 3
    back = home.put("/api/family/reward", headers=ADMIN, json={"name": "Biograftur", "cost": 2}).json()
    assert back["counts"] == "children"  # a change that leaves it out goes back to the default


def test_a_family_with_no_children_still_has_stars_that_count(home, db):
    r = home.put("/api/family/reward", headers=ADMIN, json={"name": "Pizza", "cost": 3}).json()
    assert r["counts"] == "children" and r["people"] == 3  # nobody to leave out: everyone who shares counts
    local(db, 1, timeutil.today().isoformat(), 30, user_id=1)
    assert stars(home)["reward"]["stars"] == 1


def test_an_unknown_choice_of_whose_stars_count_is_refused(home):
    assert home.put("/api/family/reward", headers=ADMIN, json={"name": "x", "cost": 5, "counts": "some"}).status_code == 422


def test_the_pace_follows_whose_stars_count(home, db):
    home.put("/api/admin/users/2/child", headers=ADMIN, json={"is_child": True})
    assert home.get("/api/family", headers=ADMIN).json()["pace"] == {"people": 1, "per_week": 3.0, "estimated": True}  # one child, a guess
    home.put("/api/family/reward", headers=ADMIN, json={"name": "x", "cost": 5, "counts": "all"})
    assert home.get("/api/family", headers=ADMIN).json()["pace"]["people"] == 3


def test_the_migration_adds_the_two_columns(proxy, db):
    c = db.get_conn()
    logs = [r["name"] for r in c.execute("PRAGMA table_info(challenge_logs)")]
    rewards = [r["name"] for r in c.execute("PRAGMA table_info(family_rewards)")]
    v = c.execute("PRAGMA user_version").fetchone()[0]
    c.close()
    assert "logged_on" in logs and "counts" in rewards and v >= 17
