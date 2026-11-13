"""One definition of "how is this week going", shared by the summary and the consistency view."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from app.domain.statuses import (
    SHORTENED_CREDIT,
    STATUS_FORKORTET,
    STATUS_GENNEMFORT,
    STATUS_PLANLAGT,
)


def iso_week_key(value: date) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def window_open(planned: date, today: date, tolerance_days: int = 1) -> bool:
    """True while an unmatched plan may still get an activity (through the last tolerance day)."""
    return today <= planned + timedelta(days=tolerance_days)


def summarize(plans: Iterable[tuple[date, str]], today: date, tolerance_days: int = 1) -> dict:
    """plans: (planned_date, status) for the mandatory runs of one week.

    A run is 'relevant' once it has an outcome: its status is no longer 'planlagt',
    or its matching window has closed. Runs still waiting are counted as 'awaiting'.
    """
    total = completed = shortened = relevant = awaiting = 0
    for planned, status in plans:
        total += 1
        waiting = status == STATUS_PLANLAGT and window_open(planned, today, tolerance_days)
        if waiting:
            awaiting += 1
            continue
        relevant += 1
        if status == STATUS_GENNEMFORT:
            completed += 1
        elif status == STATUS_FORKORTET:
            shortened += 1

    return {
        "mandatory_runs": total,
        "relevant_runs": relevant,
        "completed": completed,
        "shortened": shortened,
        "awaiting": awaiting,
    }


def adherence_pct(summary: dict) -> int:
    """Completed runs count fully, shortened runs count SHORTENED_CREDIT."""
    relevant = summary["relevant_runs"]
    if relevant <= 0:
        return 0
    credit = summary["completed"] + SHORTENED_CREDIT * summary["shortened"]
    return int(round(credit / relevant * 100))


def score(summary: dict) -> str:
    """Traffic light: Grøn (all done or nothing due yet), Gul (some done), Rød (none done)."""
    relevant = summary["relevant_runs"]
    if relevant == 0 or summary["completed"] == relevant:
        return "Grøn"
    if summary["completed"] + summary["shortened"] > 0:
        return "Gul"
    return "Rød"


def streak(run_dates: Iterable[date], today: date) -> int:
    """Consecutive weeks with at least one run, counted back from the current week.

    A current week without a run does not break the streak yet: it still has days left, so counting
    starts from last week. Once a whole week has passed without a run, the streak is over.
    """
    weeks = {iso_week_key(d) for d in run_dates}
    if not weeks:
        return 0
    cursor = today
    if iso_week_key(cursor) not in weeks:
        cursor = cursor - timedelta(days=7)
    count = 0
    while iso_week_key(cursor) in weeks:
        count += 1
        cursor = cursor - timedelta(days=7)
    return count
