"""Daily challenges (push-ups, a plank, steps...): a plan that grows slowly, and a calm picture of how it goes. Pure.

Nothing here punishes: a missed day is just a day without a tick, and a pause never ends anything. Rest days are
days the person chose not to train; they neither count nor break a streak.
"""
from __future__ import annotations

from datetime import date, timedelta

STREAK_STEPS = (7, 14, 30)  # planned days in a row


def is_rest(challenge: dict, day: date) -> bool:
    return day.weekday() in challenge["rest_weekdays"]


def target_for(challenge: dict, day: date) -> int | None:
    """The target for a day, or None before the start or on a rest day."""
    start = challenge["start_date"]
    if day < start or is_rest(challenge, day):
        return None
    steps = (day - start).days // challenge["step_every_days"]
    target = challenge["start_value"] + steps * challenge["step"]
    cap = challenge.get("cap")
    return min(target, cap) if cap else target


def day_status(challenge: dict, logs: dict[date, int], day: date, today: date) -> str:
    """done, partial (something was done, not the whole target), missed, rest, today, future or before."""
    if day < challenge["start_date"]:
        return "before"
    target = target_for(challenge, day)
    if target is None:
        return "rest"
    count = logs.get(day, 0)
    if count >= target:
        return "done"
    if day > today:
        return "future"
    if count > 0:
        return "partial"
    return "today" if day == today else "missed"


def _planned_days(challenge: dict, until: date) -> list[date]:
    out = []
    day = challenge["start_date"]
    while day <= until:
        if not is_rest(challenge, day):
            out.append(day)
        day += timedelta(days=1)
    return out


def streak(challenge: dict, logs: dict[date, int], today: date) -> int:
    """Planned days in a row that were done, counted back from today. Today not being done yet does not break it."""
    days = _planned_days(challenge, today)
    count = 0
    for day in reversed(days):
        if logs.get(day, 0) >= (target_for(challenge, day) or 0):
            count += 1
        elif day == today:
            continue
        else:
            break
    return count


def milestone_dates(challenge: dict, logs: dict[date, int], today: date) -> list[dict]:
    """The days a run of planned days in a row reached 7, 14 and 30: {key, label, date}."""
    out: list[dict] = []
    run = 0
    seen: set[int] = set()
    for day in _planned_days(challenge, today):
        if logs.get(day, 0) >= (target_for(challenge, day) or 0):
            run += 1
            if run in STREAK_STEPS and run not in seen:
                seen.add(run)
                out.append({"key": f"challenge_{challenge['id']}_{run}", "label": f"{run} dage i træk: {challenge['name']}", "date": day})
        else:
            run = 0
    return out


def best_days(challenge: dict, logs: dict[date, int]) -> list[date]:
    """The days with a new best: more than every earlier day. The first logged day is the start, not a best."""
    out: list[date] = []
    best = 0
    for day in sorted(d for d in logs if d >= challenge["start_date"]):
        if best > 0 and logs[day] > best:
            out.append(day)
        best = max(best, logs[day])
    return out


def doubled_on(challenge: dict, logs: dict[date, int]) -> date | None:
    """The first day the count reached twice the starting target."""
    goal = challenge["start_value"] * 2
    return next((d for d in sorted(logs) if d >= challenge["start_date"] and logs[d] >= goal), None)


def improvement_milestones(challenge: dict, logs: dict[date, int], today: date, window_days: int = 21) -> list[dict]:
    """Words, never numbers: 'Ny bedste dag: Armbøjninger' (only the latest one) and 'Fordoblet startmålet'."""
    cutoff = today - timedelta(days=window_days)
    out = []
    bests = [d for d in best_days(challenge, logs) if d >= cutoff]
    if bests:
        out.append({"key": f"challenge_{challenge['id']}_best", "label": f"Ny bedste dag: {challenge['name']}", "date": bests[-1]})
    doubled = doubled_on(challenge, logs)
    if doubled and doubled >= cutoff:
        out.append({"key": f"challenge_{challenge['id']}_double", "label": f"Fordoblet startmålet: {challenge['name']}", "date": doubled})
    return out


def progress(challenge: dict, logs: dict[date, int], today: date) -> dict | None:
    """From where to where, for the person and the parent: the first counted day against the best of the last week."""
    days = sorted(d for d in logs if d >= challenge["start_date"] and logs[d] > 0)
    if len(days) < 3:
        return None
    recent = [logs[d] for d in days if d >= today - timedelta(days=6)]
    return {
        "first_count": logs[days[0]],
        "recent_best": max(recent) if recent else None,
        "weeks": (today - days[0]).days // 7 + 1,
    }


def history(challenge: dict, logs: dict[date, int], today: date, days: int = 56) -> list[dict]:
    start = max(challenge["start_date"], today - timedelta(days=days - 1))
    out = []
    day = start
    while day <= today:
        out.append({"date": day.isoformat(), "target": target_for(challenge, day), "count": logs.get(day)})
        day += timedelta(days=1)
    return out


def week_days(challenge: dict, logs: dict[date, int], today: date) -> list[dict]:
    monday = today - timedelta(days=today.weekday())
    return [
        {
            "date": (monday + timedelta(days=i)).isoformat(),
            "target": target_for(challenge, monday + timedelta(days=i)),
            "count": logs.get(monday + timedelta(days=i)),
            "status": day_status(challenge, logs, monday + timedelta(days=i), today),
        }
        for i in range(7)
    ]


def summary(challenge: dict, logs: dict[date, int], today: date) -> dict:
    """Everything the person's own card needs."""
    week = week_days(challenge, logs, today)
    planned_week = [d for d in week if d["target"] is not None]
    since_start = [d for d in logs if d >= challenge["start_date"]]
    today_target = target_for(challenge, today)
    return {
        "id": challenge["id"],
        "name": challenge["name"],
        "unit": challenge["unit"],
        "today_target": today_target,
        "today_count": logs.get(today),
        "today_done": today_target is not None and logs.get(today, 0) >= today_target,
        "rest_today": today >= challenge["start_date"] and today_target is None,
        "not_started": today < challenge["start_date"],
        "streak_days": streak(challenge, logs, today),
        "done_week": sum(1 for d in planned_week if d["status"] == "done"),
        "planned_week": len(planned_week),
        "best_day": max((logs[d] for d in since_start), default=0),
        "new_best_today": today in best_days(challenge, logs),
        "progress": progress(challenge, logs, today),
        "history": history(challenge, logs, today),
        "total": sum(logs[d] for d in since_start),
        "week": week,
        "plan": {
            "start_value": challenge["start_value"],
            "step": challenge["step"],
            "step_every_days": challenge["step_every_days"],
            "cap": challenge.get("cap"),
            "rest_weekdays": sorted(challenge["rest_weekdays"]),
            "start_date": challenge["start_date"].isoformat(),
        },
    }
