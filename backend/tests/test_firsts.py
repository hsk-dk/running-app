"""First times: only ever measured against the person's own start."""
from datetime import date, timedelta

from app.domain import firsts


def d(s):
    return date.fromisoformat(s)


def run(day, km):
    return (d(day), km)


def keys(items):
    return [a["key"] for a in items]


def test_nothing_before_the_first_real_run():
    assert firsts.achieved([]) == []
    assert firsts.achieved([run("2026-01-01", 0.5)]) == []  # a warm-up is not a run
    assert firsts.next_up([], d("2026-01-05")) == []


def test_the_first_run_counts_from_one_kilometre():
    got = firsts.achieved([run("2026-01-01", 1.0)])
    assert keys(got) == ["first_run"] and got[0]["date"] == d("2026-01-01") and got[0]["label"] == "Dit første løb"
    assert firsts.achieved([run("2026-01-01", 0.99)]) == []


def test_distance_firsts_are_dated_by_the_first_run_that_reached_them():
    runs = [run("2026-01-01", 2.0), run("2026-01-05", 3.0), run("2026-01-09", 5.4), run("2026-01-12", 7.9), run("2026-01-15", 5.0)]
    got = {a["key"]: a for a in firsts.achieved(runs)}
    assert got["km_3"]["date"] == d("2026-01-05") and got["km_3"]["label"] == "Første løb på 3 km"
    assert got["km_5"]["date"] == d("2026-01-09")
    assert "km_8" not in got  # 7.9 is not 8
    assert got["first_run"]["date"] == d("2026-01-01")


def test_the_half_marathon_has_its_own_name():
    assert {a["key"]: a["label"] for a in firsts.achieved([run("2026-01-01", 21.1)])}["km_21"] == "Første halvmaraton"


def test_run_counts_are_dated_by_the_nth_run():
    runs = [run((d("2026-01-01") + timedelta(days=i)).isoformat(), 2.0) for i in range(10)]
    got = {a["key"]: a for a in firsts.achieved(runs)}
    assert got["runs_10"]["date"] == d("2026-01-10")
    assert "runs_25" not in got
    assert "runs_10" not in {a["key"] for a in firsts.achieved(runs[:9])}


def test_the_first_week_with_three_runs_is_dated_by_the_third_run():
    runs = [run("2026-01-05", 2), run("2026-01-07", 2), run("2026-01-13", 2), run("2026-01-14", 2), run("2026-01-16", 2)]  # Mon 5 and Mon 12
    got = {a["key"]: a for a in firsts.achieved(runs)}
    assert got["week_3"]["date"] == d("2026-01-16")  # the second week, its third run
    assert "week_3" not in {a["key"] for a in firsts.achieved(runs[:4])}


def test_weeks_in_a_row_need_back_to_back_weeks():
    weekly = [run((d("2026-01-05") + timedelta(days=7 * i)).isoformat(), 2) for i in range(4)]
    got = {a["key"]: a for a in firsts.achieved(weekly)}
    assert got["streak_4"]["date"] == d("2026-01-26")
    gap = [weekly[0], weekly[1], weekly[3], run("2026-02-09", 2)]
    assert "streak_4" not in {a["key"] for a in firsts.achieved(gap)}


def test_several_runs_in_one_week_count_as_one_week():
    assert "streak_4" not in {a["key"] for a in firsts.achieved([run("2026-01-05", 2), run("2026-01-06", 2), run("2026-01-07", 2), run("2026-01-08", 2)])}


def test_the_list_is_oldest_first():
    runs = [run("2026-01-01", 2.0), run("2026-01-05", 3.0), run("2026-01-09", 5.4)]
    got = firsts.achieved(runs)
    assert [a["date"] for a in got] == sorted(a["date"] for a in got)


def test_next_up_names_the_next_distance_and_gives_progress():
    n = firsts.next_up([run("2026-01-01", 2.0), run("2026-01-05", 4.1)], d("2026-01-06"))
    assert n[0] == {"key": "km_5", "label": "Første løb på 5 km", "current": 4.1, "target": 5, "unit": "km"}


def test_next_up_offers_the_next_streak_while_one_is_running_and_run_count_otherwise():
    today = d("2026-01-20")
    weeks = [run("2026-01-05", 2), run("2026-01-12", 2), run("2026-01-19", 2)]
    n = firsts.next_up(weeks, today)
    assert n[1] == {"key": "streak_4", "label": "4 uger i træk", "current": 3, "target": 4, "unit": "uger"}
    broken = firsts.next_up([run("2026-01-05", 2)], d("2026-03-01"))
    assert broken[1]["key"] == "runs_10" and broken[1]["current"] == 1


def test_next_up_is_empty_for_someone_who_has_done_everything():
    runs = [run((d("2024-01-01") + timedelta(days=i)).isoformat(), 22.0) for i in range(0, 600, 3)]
    assert all(x["key"] != "km_21" for x in firsts.next_up(runs, d("2026-12-01")))


def test_recent_keeps_only_the_last_days_including_today():
    items = [{"key": "a", "date": d("2026-01-10")}, {"key": "b", "date": d("2026-01-04")}, {"key": "c", "date": d("2026-01-03")}, {"key": "d", "date": d("2026-01-11")}]
    assert [i["key"] for i in firsts.recent(items, d("2026-01-10"))] == ["a", "b"]


# ---- through the app --------------------------------------------------------------------------------------

from tests.auth_helpers import ADMIN, FAMILY
from tests.conftest import add_activity


def local(db, id, day, km, user_id=1):
    add_activity(db, id, f"{day}T08:00:00Z", distance_m=km * 1000, user_id=user_id)
    c = db.get_conn(); c.execute("UPDATE activities SET start_date_local = ? WHERE id = ?", (f"{day}T09:00:00Z", id)); c.commit(); c.close()


def test_the_endpoint_gives_achievements_with_dates_and_what_is_next(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    local(db, 1, "2026-01-05", 2.0)
    local(db, 2, "2026-01-08", 5.2)
    r = proxy.get("/api/activities/firsts", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert [(a["key"], a["date"]) for a in body["achieved"]] == [("first_run", "2026-01-05"), ("km_3", "2026-01-08"), ("km_5", "2026-01-08")]
    assert body["next"][0]["key"] == "km_8" and body["next"][0]["current"] == 5.2
    assert all(a["is_new"] is False for a in body["achieved"])  # months ago


def test_a_milestone_reached_this_week_is_marked_new(proxy, db):
    from app.domain import timeutil
    proxy.get("/api/me", headers=ADMIN)
    today = timeutil.today().isoformat()
    local(db, 1, today, 3.4)
    got = {a["key"]: a for a in proxy.get("/api/activities/firsts", headers=ADMIN).json()["achieved"]}
    assert got["km_3"]["is_new"] is True and got["first_run"]["is_new"] is True


def test_firsts_are_only_the_signed_in_persons_own_and_empty_without_runs(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    local(db, 1, "2026-01-05", 6.0, user_id=1)
    assert proxy.get("/api/activities/firsts", headers=FAMILY).json() == {"achieved": [], "next": []}
    assert len(proxy.get("/api/activities/firsts", headers=ADMIN).json()["achieved"]) >= 3


def _family_setup(proxy, db, level):
    from app.domain import timeutil
    from app.repositories import users as users_repo
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    c = db.get_conn(); users_repo.set_sharing_level(c, 2, level); c.commit(); c.close()
    local(db, 1, timeutil.today().isoformat(), 5.5, user_id=2)
    return next(m for m in proxy.get("/api/family", headers=ADMIN).json()["members"] if m["user_id"] == 2)


def test_family_sees_recent_milestones_as_labels_and_days_only_from_the_overview_level_up(proxy, db):
    for level in ("overview", "all"):
        anna = _family_setup(proxy, db, level)
        assert {x["label"] for x in anna["new_milestones"]} >= {"Første løb", "Første løb på 5 km"}
        assert all(set(x) == {"key", "label", "date"} for x in anna["new_milestones"])  # no distance, no time
        c = db.get_conn(); c.execute("DELETE FROM activities WHERE id = 1"); c.commit(); c.close()


def test_a_private_person_shows_no_milestones(proxy, db):
    anna = _family_setup(proxy, db, "private")
    assert anna["shared"] is False and anna["new_milestones"] is None


def test_a_run_of_exactly_a_step_counts_so_the_next_step_is_the_one_after():
    assert firsts.next_up([run("2026-01-01", 5.0)], d("2026-01-02"))[0]["key"] == "km_8"
