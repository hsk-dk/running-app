from __future__ import annotations

import logging
import sqlite3
from datetime import date

from app.db import get_conn
from app.domain import timeutil, weekly
from app.domain.runs import actual_value as compute_actual_value
from app.domain.runs import is_mandatory
from app.domain.statuses import (
    STATUS_FORKORTET,
    STATUS_GENNEMFORT,
    STATUS_PLANLAGT,
    STATUS_SPRUNGET_OVER,
    compute_status,
)
from app.repositories import activities as activity_repo
from app.repositories import planned_runs as plan_repo

logger = logging.getLogger(__name__)


def _reset_auto_matches(conn: sqlite3.Connection) -> None:
    plan_repo.reset_auto_matches(
        conn,
        (STATUS_GENNEMFORT, STATUS_FORKORTET, STATUS_SPRUNGET_OVER, STATUS_PLANLAGT),
        STATUS_PLANLAGT,
    )
    activity_repo.reset_links(conn)


def _candidate_score(
    planned_row: sqlite3.Row,
    activity_row: sqlite3.Row,
    planned_date: date,
    activity_date: date,
) -> tuple[tuple[float, float, int, str, int], float, str]:
    day_diff = abs((activity_date - planned_date).days)

    target_value = planned_row["target_value"]
    actual_value = compute_actual_value(
        planned_row["target_type"], activity_row["distance_m"], activity_row["moving_time_s"]
    )

    if target_value is not None and float(target_value) > 0:
        value_diff = abs(actual_value - float(target_value))
    else:
        value_diff = 9999.0

    long_penalty = 0
    long_reason = ""
    if (planned_row["session_type"] or "").lower() == "long":
        target_amount = float(target_value or 0.0)
        if target_amount > 0 and actual_value < (target_amount * 0.8):
            long_penalty = 50
            long_reason = " + straf for kort langtur"

    score_tuple = (
        float(day_diff),
        float(value_diff),
        int(long_penalty),
        str(activity_row["start_date"]),
        int(activity_row["id"]),
    )

    flat_score = float(day_diff * 1000) + float(value_diff * 10) + float(long_penalty)

    if target_value is not None and float(target_value) > 0:
        unit = "km" if planned_row["target_type"] == "distance" else "min"
        reason = (
            f"Valgt pga. datoafstand {day_diff} dag(e) og målafvigelse "
            f"{round(value_diff, 2)} {unit}{long_reason}"
        )
    else:
        reason = f"datoafstand={day_diff} dag(e), intet måltal{long_reason}"

    return score_tuple, flat_score, reason


def evaluate_planned_runs(tolerance_days: int = 1):
    """Match plans to activities by local calendar date (within tolerance_days) and target."""
    conn = get_conn()
    try:
        _reset_auto_matches(conn)

        planned_rows = plan_repo.list_all(conn)
        activity_rows = activity_repo.list_runs(conn)
        today = timeutil.today()

        dated_activities = []
        for activity in activity_rows:
            activity_date = timeutil.activity_local_date(activity)
            if activity_date is not None:
                dated_activities.append((activity, activity_date))

        used_activity_ids: set[int] = set()
        for p in planned_rows:
            if p["manual_override"] and p["matched_activity_id"]:
                used_activity_ids.add(int(p["matched_activity_id"]))

        for planned in planned_rows:
            if planned["manual_override"]:
                continue

            try:
                planned_date = timeutil.parse_planned_date(planned["planned_date"])
            except ValueError:
                logger.warning("Plan %s has an invalid date %r; skipped", planned["id"], planned["planned_date"])
                continue

            candidates = []
            for activity, activity_date in dated_activities:
                if int(activity["id"]) in used_activity_ids:
                    continue
                if abs((activity_date - planned_date).days) <= tolerance_days:
                    score_tuple, flat_score, reason = _candidate_score(
                        planned, activity, planned_date, activity_date
                    )
                    candidates.append((activity, score_tuple, flat_score, reason))

            if not candidates:
                status = (
                    STATUS_PLANLAGT
                    if weekly.window_open(planned_date, today, tolerance_days)
                    else STATUS_SPRUNGET_OVER
                )
                plan_repo.set_status(conn, planned["id"], status)
                continue

            candidates.sort(key=lambda item: item[1])
            best, _, best_flat_score, best_reason = candidates[0]
            used_activity_ids.add(int(best["id"]))

            actual_value = compute_actual_value(
                planned["target_type"], best["distance_m"], best["moving_time_s"]
            )
            plan_repo.set_auto_match(
                conn,
                planned["id"],
                activity_id=best["id"],
                activity_date=timeutil.activity_local_date(best).isoformat(),
                activity_name=best["name"],
                actual_value=actual_value,
                status=compute_status(planned["target_value"], actual_value),
                score=best_flat_score,
                reason=best_reason,
            )
            activity_repo.set_matched_plan(conn, best["id"], planned["id"])

        activity_repo.refresh_extra_flags(conn)

        conn.commit()
        return {"updated": len(planned_rows)}
    finally:
        conn.close()


def get_weekly_consistency(tolerance_days: int = 1):
    conn = get_conn()
    try:
        weeks: dict[str, list[tuple[date, str]]] = {}
        for row in plan_repo.list_all(conn):
            if not is_mandatory(row):
                continue
            try:
                planned_date = timeutil.parse_planned_date(row["planned_date"])
            except ValueError:
                continue
            weeks.setdefault(weekly.iso_week_key(planned_date), []).append(
                (planned_date, row["status"] or STATUS_PLANLAGT)
            )

        today = timeutil.today()
        result = []
        for week in sorted(weeks):
            summary = weekly.summarize(weeks[week], today, tolerance_days)
            result.append(
                {
                    "week": week,
                    "mandatory_runs": summary["mandatory_runs"],
                    "relevant_runs": summary["relevant_runs"],
                    "completed": summary["completed"],
                    "shortened": summary["shortened"],
                    "score": weekly.score(summary),
                }
            )
        return result
    finally:
        conn.close()
