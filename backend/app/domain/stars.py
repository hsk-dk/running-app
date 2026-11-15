"""Stars: a small reward for effort, never for speed or distance. Pure.

A star is earned for an active day (15 minutes or more of any activity) and for a challenge day that was done. At most five a
week can be earned this way, so more is never better, and a star is never taken away. A parent can add bonus stars on top.
"""
from __future__ import annotations

from datetime import date, timedelta

ACTIVE_MINUTES = 15
WEEKLY_CAP = 5


def active_days(seconds_by_day: dict[date, float]) -> set[date]:
    """The days with at least ACTIVE_MINUTES of activity in total (a short walk and a short run add up)."""
    return {d for d, s in seconds_by_day.items() if s >= ACTIVE_MINUTES * 60}


def earned(active: set[date], challenge_days: set[date]) -> dict[date, int]:
    """Stars per day: one for an active day and one for a challenge day, but no more than WEEKLY_CAP in a week (Monday to Sunday).
    The cap is filled in date order, so the earliest days of the week count."""
    out: dict[date, int] = {}
    used: dict[date, int] = {}  # Monday -> stars already counted that week
    for day in sorted(active | challenge_days):
        monday = day - timedelta(days=day.weekday())
        want = (1 if day in active else 0) + (1 if day in challenge_days else 0)
        give = min(want, WEEKLY_CAP - used.get(monday, 0))
        if give > 0:
            out[day] = give
            used[monday] = used.get(monday, 0) + give
    return out


def week_of(earned_by_day: dict[date, int], bonus_by_day: dict[date, int], today: date) -> dict:
    """This week's stars for the slots on screen: earned (capped) and bonus, day by day."""
    monday = today - timedelta(days=today.weekday())
    days = [monday + timedelta(days=i) for i in range(7)]
    return {
        "cap": WEEKLY_CAP,
        "earned": sum(earned_by_day.get(d, 0) for d in days),
        "bonus": sum(bonus_by_day.get(d, 0) for d in days),
        "days": [{"date": d.isoformat(), "stars": earned_by_day.get(d, 0) + bonus_by_day.get(d, 0)} for d in days],
    }


def total(earned_by_day: dict[date, int], bonus_by_day: dict[date, int], since: date | None = None) -> int:
    """All stars, or only the ones from `since` (a day) onwards."""
    return sum(n for d, n in earned_by_day.items() if since is None or d >= since) + sum(
        n for d, n in bonus_by_day.items() if since is None or d >= since
    )


def reward_state(cost: int, stars: int) -> dict:
    return {"cost": cost, "stars": stars, "reached": stars >= cost, "remaining": max(0, cost - stars)}


RATE_DAYS = 28
BASELINE_PER_PERSON = 3.0  # stars a week a person is guessed to earn before there is anything to measure
MIN_STARS_TO_MEASURE = 4


def pace(stars_in_window: int, people: int, days: int = RATE_DAYS) -> dict:
    """How fast the family earns stars: the last four weeks, or a guess of three a week a person when there is almost nothing to go by.

    This is what lets a parent set a reward that comes neither too rarely (it stops being worth it) nor too often (it stops being special)."""
    if people <= 0:
        return {"per_week": 0.0, "estimated": True}
    if stars_in_window < MIN_STARS_TO_MEASURE:
        return {"per_week": round(people * BASELINE_PER_PERSON, 1), "estimated": True}
    return {"per_week": round(stars_in_window / (days / 7), 1), "estimated": False}


def weeks_left(remaining: int, per_week: float) -> float | None:
    """About how many weeks until the reward at the current pace, or None when nothing is being earned."""
    if remaining <= 0:
        return 0.0
    if per_week <= 0:
        return None
    return round(remaining / per_week, 1)


def suggested_cost(per_week: float, weeks: float) -> int:
    """What a reward should cost to come about every `weeks` weeks at this pace (never below 5, so it is not instant)."""
    return max(5, round(per_week * weeks))
