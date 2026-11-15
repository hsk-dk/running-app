"""The shelf of badges: each one earned once, on the day it was first reached, and never about anyone else."""
from datetime import date, timedelta

from app.domain import badges


def d(s):
    return date.fromisoformat(s)


TODAY = d("2026-11-15")
NO_CHALLENGE = {"streaks": {}, "best": None, "double": None}


def keys(items):
    return [b["key"] for b in items]


def test_the_catalogue_has_unique_keys_and_something_in_every_group():
    assert len(set(badges.KEYS)) == len(badges.KEYS) == len(badges.CATALOGUE)
    assert {c[1] for c in badges.CATALOGUE} == {"løb", "udfordring", "stjerner"}
    assert all(c[3] and c[4] and c[5] and c[2] for c in badges.CATALOGUE)  # a title, two texts and an icon on each


def test_an_empty_shelf_has_everything_still_ahead():
    s = badges.shelf([], NO_CHALLENGE, {}, TODAY)
    assert s["earned"] == [] and len(s["ahead"]) == s["total"] == len(badges.CATALOGUE)
    assert keys(s["ahead"]) == badges.KEYS  # in the order of the catalogue


def test_running_badges_come_from_the_first_times_and_unknown_keys_are_ignored():
    firsts = [{"key": "first_run", "date": d("2026-10-01")}, {"key": "km_5", "date": d("2026-11-01")}, {"key": "something_new", "date": d("2026-11-02")}]
    s = badges.shelf(firsts, NO_CHALLENGE, {}, TODAY)
    assert keys(s["earned"]) == ["km_5", "first_run"]  # newest first
    assert "km_5" not in keys(s["ahead"]) and "first_run" not in keys(s["ahead"]) and len(s["ahead"]) == len(badges.CATALOGUE) - 2


def test_challenge_badges_come_from_the_challenge_milestones():
    ch = {"streaks": {7: d("2026-11-08"), 14: d("2026-11-15")}, "best": d("2026-11-03"), "double": d("2026-11-10")}
    got = {b["key"]: b["date"] for b in badges.shelf([], ch, {}, TODAY)["earned"]}
    assert got == {"challenge_7": d("2026-11-08"), "challenge_14": d("2026-11-15"), "challenge_best": d("2026-11-03"), "challenge_double": d("2026-11-10")}
    assert "challenge_30" in keys(badges.shelf([], ch, {}, TODAY)["ahead"])


def test_a_streak_step_that_is_not_in_the_catalogue_does_not_make_a_badge():
    assert badges.shelf([], {"streaks": {99: d("2026-11-08")}, "best": None, "double": None}, {}, TODAY)["earned"] == []


def test_star_badges_are_dated_by_the_day_the_running_total_reached_the_step():
    stars = {d("2026-11-02"): 1, d("2026-11-03"): 4, d("2026-11-04"): 5, d("2026-11-09"): 2}  # running: 1, 5, 10, 12
    assert badges.star_dates(stars) == {1: d("2026-11-02"), 10: d("2026-11-04")}
    got = {b["key"]: b["date"] for b in badges.shelf([], NO_CHALLENGE, stars, TODAY)["earned"]}
    assert got == {"stars_1": d("2026-11-02"), "stars_10": d("2026-11-04")}
    assert badges.star_dates({}) == {}
    assert badges.star_dates({d("2026-11-02"): 100})[100] == d("2026-11-02")  # one big day reaches every step at once


def test_a_badge_is_new_for_a_week_and_not_after():
    firsts = [{"key": "first_run", "date": TODAY - timedelta(days=6)}, {"key": "km_3", "date": TODAY - timedelta(days=7)}, {"key": "km_5", "date": TODAY}]
    by = {b["key"]: b["is_new"] for b in badges.shelf(firsts, NO_CHALLENGE, {}, TODAY)["earned"]}
    assert by == {"first_run": True, "km_3": False, "km_5": True}


def test_two_badges_on_the_same_day_keep_a_steady_order():
    firsts = [{"key": "first_run", "date": d("2026-11-01")}, {"key": "km_3", "date": d("2026-11-01")}, {"key": "week_3", "date": d("2026-11-01")}]
    a = keys(badges.shelf(firsts, NO_CHALLENGE, {}, TODAY)["earned"])
    assert a == keys(badges.shelf(list(reversed(firsts)), NO_CHALLENGE, {}, TODAY)["earned"])
    assert a == ["week_3", "km_3", "first_run"]  # later in the catalogue first, on a shared day
