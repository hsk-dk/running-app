"""The plan and the calm picture of how a daily challenge goes."""
from datetime import date, timedelta

from app.domain import challenges as c


def d(s):
    return date.fromisoformat(s)


def ch(**over):
    base = {"id": 1, "name": "Armbøjninger", "unit": "stk", "start_date": d("2026-11-02"), "start_value": 5, "step": 1, "step_every_days": 7,
            "cap": None, "rest_weekdays": []}
    return {**base, **over}


def test_the_target_starts_at_the_start_value_and_grows_every_so_many_days():
    p = ch()  # Monday 2 November
    assert c.target_for(p, d("2026-11-02")) == 5
    assert c.target_for(p, d("2026-11-08")) == 5  # the last day of week one
    assert c.target_for(p, d("2026-11-09")) == 6
    assert c.target_for(p, d("2026-11-23")) == 8
    assert c.target_for(ch(step_every_days=1), d("2026-11-05")) == 8
    assert c.target_for(ch(step=0), d("2026-12-24")) == 5


def test_nothing_before_the_start_and_a_cap_stops_the_growth():
    assert c.target_for(ch(), d("2026-11-01")) is None
    assert c.target_for(ch(cap=7), d("2026-12-24")) == 7
    assert c.target_for(ch(cap=None), d("2026-12-24")) > 7


def test_rest_days_have_no_target():
    p = ch(rest_weekdays=[6])  # Sundays
    assert c.target_for(p, d("2026-11-08")) is None
    assert c.target_for(p, d("2026-11-07")) == 5
    assert c.is_rest(p, d("2026-11-08")) and not c.is_rest(p, d("2026-11-09"))


def test_day_status_is_calm():
    p = ch(rest_weekdays=[6])
    logs = {d("2026-11-02"): 5, d("2026-11-03"): 3, d("2026-11-04"): 9}
    today = d("2026-11-06")
    assert c.day_status(p, logs, d("2026-11-01"), today) == "before"
    assert c.day_status(p, logs, d("2026-11-02"), today) == "done"
    assert c.day_status(p, logs, d("2026-11-03"), today) == "partial"  # something, not the whole target
    assert c.day_status(p, logs, d("2026-11-04"), today) == "done"  # more than the target is done
    assert c.day_status(p, logs, d("2026-11-05"), today) == "missed"
    assert c.day_status(p, logs, d("2026-11-06"), today) == "today"
    assert c.day_status(p, logs, d("2026-11-07"), today) == "future"
    assert c.day_status(p, logs, d("2026-11-08"), today) == "rest"
    assert c.day_status(p, {d("2026-11-06"): 5}, d("2026-11-06"), today) == "done"


def test_a_streak_counts_planned_days_done_and_ignores_rest_days():
    p = ch(rest_weekdays=[6], step=0)
    logs = {d("2026-11-05"): 5, d("2026-11-06"): 5, d("2026-11-07"): 5, d("2026-11-09"): 5}  # Thu Fri Sat, rest on Sunday, Mon
    assert c.streak(p, logs, d("2026-11-09")) == 4
    assert c.streak(p, {d("2026-11-05"): 5, d("2026-11-07"): 5}, d("2026-11-09")) == 1  # Saturday done, Friday missed: the run is just Saturday (Sunday rest, Monday not done yet)
    assert c.streak(p, logs, d("2026-11-10")) == 4  # Tuesday not done yet does not break it


def test_today_not_yet_done_does_not_break_but_yesterday_missed_does():
    p = ch(step=0)
    done = {d("2026-11-03"): 5, d("2026-11-04"): 5}
    assert c.streak(p, done, d("2026-11-05")) == 2
    assert c.streak(p, done, d("2026-11-06")) == 0  # Wednesday was missed
    assert c.streak(p, {d("2026-11-05"): 5}, d("2026-11-05")) == 1


def test_milestones_are_dated_by_the_day_the_run_reached_seven_fourteen_and_thirty():
    p = ch(step=0)
    logs = {d("2026-11-02") + timedelta(days=i): 5 for i in range(15)}
    got = {m["key"]: m for m in c.milestone_dates(p, logs, d("2026-11-16"))}
    assert got["challenge_1_7"]["date"] == d("2026-11-08") and got["challenge_1_7"]["label"] == "7 dage i træk: Armbøjninger"
    assert got["challenge_1_14"]["date"] == d("2026-11-15")
    assert "challenge_1_30" not in got
    broken = dict(logs); del broken[d("2026-11-05")]
    assert "challenge_1_7" not in {m["key"] for m in c.milestone_dates(p, broken, d("2026-11-09"))}


def test_the_summary_for_the_card():
    p = ch(rest_weekdays=[6])
    logs = {d("2026-11-02"): 5, d("2026-11-03"): 7, d("2026-11-04"): 3}
    s = c.summary(p, logs, d("2026-11-05"))
    assert s["today_target"] == 5 and s["today_count"] is None and s["today_done"] is False
    assert s["done_week"] == 2 and s["planned_week"] == 6  # Mon-Sat planned; Tue 7 and Mon 5 done, Wed 3 partial
    assert s["best_day"] == 7 and s["total"] == 15
    assert [x["status"] for x in s["week"]] == ["done", "done", "partial", "today", "future", "future", "rest"]
    assert s["week"][0]["date"] == "2026-11-02" and s["week"][6]["target"] is None
    assert s["plan"] == {"start_value": 5, "step": 1, "step_every_days": 7, "cap": None, "rest_weekdays": [6], "start_date": "2026-11-02"}
    assert c.summary(p, logs, d("2026-11-08"))["rest_today"] is True
    assert c.summary(p, logs, d("2026-10-30"))["not_started"] is True


def test_logs_before_the_start_do_not_count():
    s = c.summary(ch(), {d("2026-10-01"): 99, d("2026-11-02"): 5}, d("2026-11-02"))
    assert s["best_day"] == 5 and s["total"] == 5


def test_thirty_days_in_a_row_is_a_milestone_and_only_the_first_time_counts():
    p = ch(step=0)
    month = {d("2026-11-02") + timedelta(days=i): 5 for i in range(31)}
    assert "challenge_1_30" in {m["key"] for m in c.milestone_dates(p, month, d("2026-12-02"))}
    again = {d("2026-11-02") + timedelta(days=i): 5 for i in range(7)}
    again.update({d("2026-11-12") + timedelta(days=i): 5 for i in range(7)})  # a second run of seven after a pause
    got = [m for m in c.milestone_dates(p, again, d("2026-11-20")) if m["key"] == "challenge_1_7"]
    assert len(got) == 1 and got[0]["date"] == d("2026-11-08")


def test_a_challenge_without_logs_has_a_best_day_of_zero_and_today_is_just_today():
    s = c.summary(ch(), {}, d("2026-11-05"))
    assert s["best_day"] == 0 and s["total"] == 0 and s["streak_days"] == 0
    assert c.day_status(ch(), {}, d("2026-11-05"), d("2026-11-05")) == "today"
