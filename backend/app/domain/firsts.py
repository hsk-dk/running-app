"""'First times': the milestones that mean something when you are starting out. Pure.

They only ever compare a person with their own start, never with anyone else. A run shorter than MIN_RUN_KM is a warm-up
or an aborted recording and does not count.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.domain.weekly import iso_week_key

MIN_RUN_KM = 1.0
KM_STEPS = (3, 5, 8, 10, 15, 21)
RUN_COUNTS = (10, 25, 50, 100)
STREAKS = (4, 8, 12, 26, 52)  # consecutive weeks with a run

Run = tuple[date, float]  # local date, kilometres


def _runs(runs: list[Run]) -> list[Run]:
    return sorted((r for r in runs if r[1] >= MIN_RUN_KM), key=lambda r: (r[0], r[1]))


def _km_label(km: int) -> str:
    return "Første halvmaraton" if km == 21 else f"Første løb på {km} km"


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _streak_ends(runs: list[Run]) -> dict[int, date]:
    """For each streak target reached: the date of the last run of the week that completed it."""
    weeks: dict[date, date] = {}
    for d, _ in runs:
        start = _week_start(d)
        if start not in weeks or d > weeks[start]:
            weeks[start] = d
    out: dict[int, date] = {}
    count = 0
    previous: date | None = None
    for start in sorted(weeks):
        count = count + 1 if previous is not None and start - previous == timedelta(days=7) else 1
        previous = start
        for target in STREAKS:
            if count == target and target not in out:
                out[target] = weeks[start]
    return out


def achieved(all_runs: list[Run]) -> list[dict]:
    """What the person has done for the first time, oldest first: {key, label, date}."""
    runs = _runs(all_runs)
    if not runs:
        return []
    out = [{"key": "first_run", "label": "Dit første løb", "date": runs[0][0]}]
    for km in KM_STEPS:
        hit = next((d for d, k in runs if k >= km), None)
        if hit:
            out.append({"key": f"km_{km}", "label": _km_label(km), "date": hit})
    for n in RUN_COUNTS:
        if len(runs) >= n:
            out.append({"key": f"runs_{n}", "label": f"{n} løb i alt", "date": runs[n - 1][0]})
    per_week: dict[date, list[date]] = {}
    for d, _ in runs:
        per_week.setdefault(_week_start(d), []).append(d)
    for start in sorted(per_week):
        if len(per_week[start]) >= 3:
            out.append({"key": "week_3", "label": "Første uge med 3 løb", "date": per_week[start][2]})
            break
    for target, d in sorted(_streak_ends(runs).items()):
        out.append({"key": f"streak_{target}", "label": f"{target} uger i træk", "date": d})
    return sorted(out, key=lambda a: (a["date"], a["key"]))


def next_up(all_runs: list[Run], today: date) -> list[dict]:
    """The next one or two things to look forward to: {key, label, current, target, unit}. Empty when there is nothing to say yet."""
    runs = _runs(all_runs)
    if not runs:
        return []
    out: list[dict] = []
    longest = max(k for _, k in runs)
    step = next((km for km in KM_STEPS if longest < km), None)
    if step:
        out.append({"key": f"km_{step}", "label": _km_label(step), "current": round(longest, 1), "target": step, "unit": "km"})
    count = next((n for n in RUN_COUNTS if len(runs) < n), None)
    streak_now = _current_streak(runs, today)
    streak_next = next((s for s in STREAKS if streak_now < s), None)
    if streak_next and streak_now >= 1:
        out.append({"key": f"streak_{streak_next}", "label": f"{streak_next} uger i træk", "current": streak_now, "target": streak_next, "unit": "uger"})
    elif count:
        out.append({"key": f"runs_{count}", "label": f"{count} løb i alt", "current": len(runs), "target": count, "unit": "løb"})
    return out[:2]


def _current_streak(runs: list[Run], today: date) -> int:
    weeks = {iso_week_key(d) for d, _ in runs}
    cursor = today if iso_week_key(today) in weeks else today - timedelta(days=7)
    count = 0
    while iso_week_key(cursor) in weeks:
        count += 1
        cursor -= timedelta(days=7)
    return count


def recent(items: list[dict], today: date, days: int = 7) -> list[dict]:
    """Those achieved within the last `days` days, today included."""
    cutoff = today - timedelta(days=days - 1)
    return [a for a in items if cutoff <= a["date"] <= today]
