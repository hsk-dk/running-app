from __future__ import annotations

import logging
import sqlite3

from app.db import get_conn
from app.domain import timeutil, weekly
from app.domain.matching import candidate_score
from app.domain.runs import actual_value as compute_actual_value
from app.domain.runs import is_mandatory
from app.domain.statuses import (
    STATUS_FORKORTET,
    STATUS_FLYTTET,
    STATUS_GENNEMFORT,
    STATUS_PLANLAGT,
    STATUS_SPRUNGET_OVER,
    compute_status,
)
from app.errors import NotFoundError
from app.repositories import activities as activity_repo
from app.repositories import planned_runs as plan_repo

logger = logging.getLogger(__name__)


def rebuild_activity_links(user_id: int):
    conn = get_conn()
    try:
        activity_repo.mark_all_extra(conn, user_id)
        activity_repo.link_from_planned_runs(conn, user_id)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def _reset_auto_matches(conn: sqlite3.Connection, user_id: int) -> None:
    plan_repo.reset_auto_matches(
        conn, user_id,
        (STATUS_GENNEMFORT, STATUS_FORKORTET, STATUS_SPRUNGET_OVER, STATUS_PLANLAGT),
        STATUS_PLANLAGT,
    )
    activity_repo.reset_links(conn, user_id)


def evaluate_planned_runs(user_id: int, tolerance_days: int = 1):
    """Match plans to activities by local calendar date (within tolerance_days) and target."""
    conn = get_conn()
    try:
        _reset_auto_matches(conn, user_id)

        planned_rows = plan_repo.list_all(conn, user_id)
        activity_rows = activity_repo.list_runs(conn, user_id)
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
                    score_tuple, flat_score, reason = candidate_score(
                        planned, activity, planned_date, activity_date
                    )
                    candidates.append((activity, score_tuple, flat_score, reason))

            if not candidates:
                status = (
                    STATUS_PLANLAGT
                    if weekly.window_open(planned_date, today, tolerance_days)
                    else STATUS_SPRUNGET_OVER
                )
                plan_repo.set_status(conn, user_id, planned["id"], status)
                continue

            candidates.sort(key=lambda item: item[1])
            best, _, best_flat_score, best_reason = candidates[0]
            used_activity_ids.add(int(best["id"]))

            actual_value = compute_actual_value(
                planned["target_type"], best["distance_m"], best["moving_time_s"]
            )
            plan_repo.set_auto_match(
                conn, user_id,
                planned["id"],
                activity_id=best["id"],
                activity_date=timeutil.activity_local_date(best).isoformat(),
                activity_name=best["name"],
                actual_value=actual_value,
                status=compute_status(planned["target_value"], actual_value),
                score=best_flat_score,
                reason=best_reason,
            )
            activity_repo.set_matched_plan(conn, user_id, best["id"], planned["id"])

        activity_repo.refresh_extra_flags(conn, user_id)

        conn.commit()
        return {"updated": len(planned_rows)}
    finally:
        conn.close()


def evaluate_and_sync(user_id: int):
    result = evaluate_planned_runs(user_id)
    rebuild_activity_links(user_id)
    return result


def _display_target(row) -> str:
    target_type = row["target_type"] or "time"
    value = row["target_value"]
    if value is None:
        return "-"
    if target_type == "distance":
        return f"{value:.1f} km"
    return f"{int(value)} min"


def _display_actual(row) -> str:
    value = row["actual_value"]
    if value is None:
        return "-"
    target_type = row["target_type"] or "time"
    if target_type == "distance":
        return f"{value:.1f} km"
    return f"{round(value, 1)} min"


def _serialize_planned_run(row):
    return {
        "id": row["id"],
        "planned_date": row["planned_date"],
        "session_type": row["session_type"],
        "target_type": row["target_type"] or "time",
        "target_value": row["target_value"],
        "mandatory": is_mandatory(row),
        "optional": not is_mandatory(row),
        "notes": row["notes"],
        "status": row["status"] or STATUS_PLANLAGT,
        "manual_override": bool(row["manual_override"]),
        "override_reason": row["override_reason"],
        "matched_activity_id": row["matched_activity_id"],
        "matched_activity_date": row["matched_activity_date"],
        "matched_activity_name": row["matched_activity_name"],
        "actual_value": row["actual_value"],
        "display_target": _display_target(row),
        "display_actual": _display_actual(row),
        "evaluated_at": row["evaluated_at"],
        "match_score": row["match_score"],
        "match_reason": row["match_reason"],
    }


def list_planned_runs(user_id: int):
    conn = get_conn()
    try:
        return [_serialize_planned_run(r) for r in plan_repo.list_all(conn, user_id)]
    finally:
        conn.close()


def add_planned_run(user_id: int, data: dict):
    conn = get_conn()
    try:
        target_type = data.get("target_type", "time")
        target_value = data.get("target_value")

        if target_value is None:
            target_value = data.get("target_minutes")

        plan_id = plan_repo.insert(
            conn, user_id,
            planned_date=data["planned_date"],
            session_type=data["session_type"],
            target_minutes=data.get("target_minutes"),
            optional=int(data.get("optional", False)),
            notes=data.get("notes"),
            status=STATUS_PLANLAGT,
            target_type=target_type,
            target_value=target_value,
            mandatory=int(not bool(data.get("optional", False))),
        )
        conn.commit()
        return _serialize_planned_run(plan_repo.get(conn, user_id, plan_id))
    finally:
        conn.close()


def _require_plan(conn, user_id: int, planned_run_id: int):
    row = plan_repo.get(conn, user_id, planned_run_id)
    if row is None:
        raise NotFoundError(f"Planned run {planned_run_id} not found")
    return row


def _manual_status(user_id: int, planned_run_id: int, status: str, reason: str):
    conn = get_conn()
    try:
        _require_plan(conn, user_id, planned_run_id)
        plan_repo.set_manual_status(conn, user_id, planned_run_id, status, reason)
        activity_repo.clear_links_for_plan(conn, user_id, planned_run_id)
        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync(user_id)


def mark_planned_run_skipped(user_id: int, planned_run_id: int):
    return _manual_status(user_id, planned_run_id, STATUS_SPRUNGET_OVER, "manuelt sprunget over")


def mark_planned_run_rescheduled(user_id: int, planned_run_id: int):
    return _manual_status(user_id, planned_run_id, STATUS_FLYTTET, "manuelt flyttet")


def clear_planned_run_match(user_id: int, planned_run_id: int):
    conn = get_conn()
    try:
        row = _require_plan(conn, user_id, planned_run_id)
        matched_activity_id = row["matched_activity_id"]

        plan_repo.set_manual_status(
            conn, user_id, planned_run_id, STATUS_PLANLAGT, "match fjernet manuelt"
        )
        if matched_activity_id:
            activity_repo.clear_link_for_activity(conn, user_id, matched_activity_id)

        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync(user_id)


def match_activity_to_planned_run(user_id: int, planned_run_id: int, activity_id: int):
    conn = get_conn()
    try:
        planned = _require_plan(conn, user_id, planned_run_id)
        activity = activity_repo.get(conn, user_id, activity_id)
        if activity is None:
            raise NotFoundError(f"Activity {activity_id} not found")

        actual_value = compute_actual_value(
            planned["target_type"], activity["distance_m"], activity["moving_time_s"]
        )
        status = compute_status(planned["target_value"], actual_value)

        activity_repo.clear_links_for_plan(conn, user_id, planned_run_id)
        plan_repo.clear_matched_activity_id(conn, user_id, activity_id)
        plan_repo.set_manual_match(
            conn, user_id,
            planned_run_id,
            activity_id=activity_id,
            activity_date=str(activity["start_date"])[:10],
            activity_name=activity["name"],
            actual_value=actual_value,
            status=status,
        )
        activity_repo.set_matched_plan(conn, user_id, activity_id, planned_run_id, is_extra=0)

        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync(user_id)


def update_planned_run(user_id: int, planned_run_id: int, data: dict):
    conn = get_conn()
    try:
        _require_plan(conn, user_id, planned_run_id)
        plan_repo.update_from_edit(
            conn, user_id,
            planned_run_id,
            planned_date=data["planned_date"],
            session_type=data["session_type"],
            target_type=data["target_type"],
            target_value=data["target_value"],
            optional=int(data.get("optional", False)),
            notes=data.get("notes"),
        )
        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync(user_id)


def delete_planned_run(user_id: int, planned_run_id: int):
    conn = get_conn()
    try:
        _require_plan(conn, user_id, planned_run_id)
        activity_repo.clear_links_for_plan(conn, user_id, planned_run_id)
        plan_repo.delete(conn, user_id, planned_run_id)
        conn.commit()
    finally:
        conn.close()

    rebuild_activity_links(user_id)
    return {"deleted": planned_run_id}
