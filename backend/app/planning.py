from app.db import get_conn
from app.repositories import activities as activity_repo
from app.repositories import planned_runs as plan_repo
from app.matching import (
    STATUS_PLANLAGT,
    STATUS_SPRUNGET_OVER,
    STATUS_FLYTTET,
    evaluate_planned_runs,
)


def rebuild_activity_links():
    conn = get_conn()
    try:
        activity_repo.mark_all_extra(conn)
        activity_repo.link_from_planned_runs(conn)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def evaluate_and_sync():
    result = evaluate_planned_runs()
    rebuild_activity_links()
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
        "mandatory": bool(row["mandatory"]),
        "optional": not bool(row["mandatory"]),
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


def list_planned_runs():
    conn = get_conn()
    try:
        return [_serialize_planned_run(r) for r in plan_repo.list_all(conn)]
    finally:
        conn.close()


def add_planned_run(data: dict):
    conn = get_conn()
    try:
        target_type = data.get("target_type", "time")
        target_value = data.get("target_value")

        if target_value is None:
            target_value = data.get("target_minutes")

        plan_id = plan_repo.insert(
            conn,
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
        return _serialize_planned_run(plan_repo.get(conn, plan_id))
    finally:
        conn.close()


def _manual_status(planned_run_id: int, status: str, reason: str):
    conn = get_conn()
    try:
        plan_repo.set_manual_status(conn, planned_run_id, status, reason)
        activity_repo.clear_links_for_plan(conn, planned_run_id)
        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def mark_planned_run_skipped(planned_run_id: int):
    return _manual_status(planned_run_id, STATUS_SPRUNGET_OVER, "manuelt sprunget over")


def mark_planned_run_rescheduled(planned_run_id: int):
    return _manual_status(planned_run_id, STATUS_FLYTTET, "manuelt flyttet")


def clear_planned_run_match(planned_run_id: int):
    conn = get_conn()
    try:
        row = plan_repo.get(conn, planned_run_id)
        matched_activity_id = row["matched_activity_id"] if row else None

        plan_repo.set_manual_status(
            conn, planned_run_id, STATUS_PLANLAGT, "match fjernet manuelt"
        )
        if matched_activity_id:
            activity_repo.clear_link_for_activity(conn, matched_activity_id)

        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def match_activity_to_planned_run(planned_run_id: int, activity_id: int):
    conn = get_conn()
    try:
        activity = activity_repo.get(conn, activity_id)
        planned = plan_repo.get(conn, planned_run_id)

        if not activity or not planned:
            raise ValueError("Planned run or activity not found")

        target_type = planned["target_type"] or "time"
        actual_value = (
            float(activity["distance_m"] or 0.0) / 1000.0
            if target_type == "distance"
            else float(activity["moving_time_s"] or 0.0) / 60.0
        )

        target_value = planned["target_value"] or 0.0
        ratio = actual_value / float(target_value) if target_value else 0.0
        if ratio >= 0.9:
            status = "gennemført"
        elif ratio >= 0.5:
            status = "forkortet"
        else:
            status = "sprunget over"

        activity_repo.clear_links_for_plan(conn, planned_run_id)
        plan_repo.clear_matched_activity_id(conn, activity_id)
        plan_repo.set_manual_match(
            conn,
            planned_run_id,
            activity_id=activity_id,
            activity_date=str(activity["start_date"])[:10],
            activity_name=activity["name"],
            actual_value=actual_value,
            status=status,
        )
        activity_repo.set_matched_plan(conn, activity_id, planned_run_id, is_extra=0)

        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def update_planned_run(planned_run_id: int, data: dict):
    conn = get_conn()
    try:
        plan_repo.update_from_edit(
            conn,
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

    return evaluate_and_sync()


def delete_planned_run(planned_run_id: int):
    conn = get_conn()
    try:
        activity_repo.clear_links_for_plan(conn, planned_run_id)
        plan_repo.delete(conn, planned_run_id)
        conn.commit()
    finally:
        conn.close()

    rebuild_activity_links()
    return {"deleted": planned_run_id}
