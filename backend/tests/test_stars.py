"""Stars reward effort, never speed or distance, with a weekly cap and nothing ever taken away."""
from datetime import date, timedelta

from app.domain import stars


def d(s):
    return date.fromisoformat(s)


MON = d("2026-11-09")


def days(*offsets):
    return {MON + timedelta(days=i) for i in offsets}


def test_a_day_is_active_from_fifteen_minutes_in_total():
    secs = {d("2026-11-09"): 15 * 60, d("2026-11-10"): 15 * 60 - 1, d("2026-11-11"): 600}
    assert stars.active_days(secs) == {d("2026-11-09")}
    assert stars.active_days({d("2026-11-11"): 600 + 300}) == {d("2026-11-11")}  # the pieces of a day add up (done by the caller)
    assert stars.active_days({}) == set()


def test_one_star_for_an_active_day_one_for_a_challenge_day_and_both_on_the_same_day():
    e = stars.earned(days(0, 2), days(2, 3))
    assert e == {MON: 1, MON + timedelta(days=2): 2, MON + timedelta(days=3): 1}


def test_at_most_five_a_week_and_the_earliest_days_count():
    e = stars.earned(days(0, 1, 2, 3, 4, 5, 6), days(0, 1, 2, 3, 4, 5, 6))  # 14 possible
    assert sum(e.values()) == stars.WEEKLY_CAP == 5
    assert e == {MON: 2, MON + timedelta(days=1): 2, MON + timedelta(days=2): 1}
    assert MON + timedelta(days=6) not in e


def test_the_cap_is_per_week_and_a_week_starts_on_monday():
    e = stars.earned(days(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13), set())  # two full weeks of active days
    assert sum(v for k, v in e.items() if k < MON + timedelta(days=7)) == 5
    assert sum(v for k, v in e.items() if k >= MON + timedelta(days=7)) == 5
    assert (MON + timedelta(days=7)) in e  # the next Monday starts afresh


def test_a_day_that_would_go_over_the_cap_gives_only_what_is_left():
    e = stars.earned(days(0, 1, 2), days(0, 1, 2))  # 6 wanted, 5 allowed
    assert e[MON + timedelta(days=2)] == 1 and sum(e.values()) == 5


def test_nothing_without_activity_and_days_are_never_negative():
    assert stars.earned(set(), set()) == {}


def test_the_week_on_screen_has_seven_days_and_adds_earned_and_bonus():
    e = {MON: 1, MON + timedelta(days=2): 2, MON - timedelta(days=1): 2}  # the last one is last Sunday: another week
    b = {MON + timedelta(days=2): 1, MON + timedelta(days=9): 4}
    w = stars.week_of(e, b, MON + timedelta(days=3))
    assert (w["cap"], w["earned"], w["bonus"]) == (5, 3, 1)
    assert [x["stars"] for x in w["days"]] == [1, 0, 3, 0, 0, 0, 0]
    assert w["days"][0]["date"] == "2026-11-09" and len(w["days"]) == 7


def test_total_counts_everything_or_only_from_a_day_on():
    e = {d("2026-11-09"): 2, d("2026-11-12"): 1}
    b = {d("2026-11-10"): 1}
    assert stars.total(e, b) == 4
    assert stars.total(e, b, since=d("2026-11-10")) == 2
    assert stars.total(e, b, since=d("2026-11-12")) == 1
    assert stars.total({}, {}) == 0


def test_a_reward_is_reached_at_exactly_the_cost():
    assert stars.reward_state(40, 39) == {"cost": 40, "stars": 39, "reached": False, "remaining": 1}
    assert stars.reward_state(40, 40)["reached"] is True and stars.reward_state(40, 40)["remaining"] == 0
    assert stars.reward_state(40, 55)["remaining"] == 0


# ---- the balance: how fast stars come against what a reward costs --------------------------------------------------

def test_pace_is_measured_over_four_weeks_and_guessed_when_there_is_nothing_to_go_by():
    assert stars.pace(28, 3) == {"per_week": 7.0, "estimated": False}  # 28 stars in 4 weeks
    assert stars.pace(10, 2) == {"per_week": 2.5, "estimated": False}
    assert stars.pace(3, 3) == {"per_week": 9.0, "estimated": True}  # too little to measure: three a week a person
    assert stars.pace(0, 2) == {"per_week": 6.0, "estimated": True}
    assert stars.pace(4, 2)["estimated"] is False  # four is enough
    assert stars.pace(50, 0) == {"per_week": 0.0, "estimated": True}


def test_weeks_left_is_how_long_at_this_pace_and_nothing_when_nothing_is_earned():
    assert stars.weeks_left(28, 7.0) == 4.0
    assert stars.weeks_left(10, 4.0) == 2.5
    assert stars.weeks_left(0, 0.0) == 0.0  # already there
    assert stars.weeks_left(-3, 5.0) == 0.0
    assert stars.weeks_left(10, 0.0) is None


def test_a_suggested_cost_follows_the_pace_and_is_never_instant():
    assert stars.suggested_cost(9.0, 3) == 27
    assert stars.suggested_cost(7.0, 2) == 14
    assert stars.suggested_cost(1.0, 1) == 5
    assert stars.suggested_cost(0.0, 4) == 5
    assert stars.suggested_cost(8.5, 2) == 17
