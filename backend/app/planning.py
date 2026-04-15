from app.db import get_conn
from app.matching import (
    STATUS_PLANLAGT,
    STATUS_SPRUNGET_OVER,
    STATUS_FLYTTET,
    evaluate_planned_runs,
)


def rebuild_activity_links():
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE activities
            SET
                matched_planned_run_id = NULL,
                is_extra = 1
            """
        )

        conn.execute(
            """
            UPDATE activities
            SET
                matched_planned_run_id = (
                    SELECT p.id
                    FROM planned_runs p
                    WHERE p.matched_activity_id = activities.id
                    LIMIT 1
                ),
                is_extra = 0
            WHERE EXISTS (
                SELECT 1
                FROM planned_runs p
                WHERE p.matched_activity_id = activities.id
            )
            """
        )

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
        rows = conn.execute(
            """
            SELECT *
            FROM planned_runs
            ORDER BY planned_date, id
            """
        ).fetchall()
        return [_serialize_planned_run(r) for r in rows]
    finally:
        conn.close()


def add_planned_run(data: dict):
    conn = get_conn()
    try:
        target_type = data.get("target_type", "time")
        target_value = data.get("target_value")

        if target_value is None:
            target_value = data.get("target_minutes")

        mandatory = int(not bool(data.get("optional", False)))

        cur = conn.execute(
            """
            INSERT INTO planned_runs (
                planned_date,
                session_type,
                target_minutes,
                optional,
                notes,
                status,
                target_type,
                target_value,
                mandatory,
                manual_override,
                match_score,
                match_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)
            """,
            (
                data["planned_date"],
                data["session_type"],
                data.get("target_minutes"),
                int(data.get("optional", False)),
                data.get("notes"),
                STATUS_PLANLAGT,
                target_type,
                target_value,
                mandatory,
            ),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM planned_runs WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _serialize_planned_run(row)
    finally:
        conn.close()


def mark_planned_run_skipped(planned_run_id: int):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE planned_runs
            SET
                status = ?,
                manual_override = 1,
                override_reason = 'manuelt sprunget over',
                matched_activity_id = NULL,
                matched_activity_date = NULL,
                matched_activity_name = NULL,
                actual_value = NULL,
                match_score = NULL,
                match_reason = NULL,
                evaluated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (STATUS_SPRUNGET_OVER, planned_run_id),
        )
        conn.execute(
            """
            UPDATE activities
            SET matched_planned_run_id = NULL
            WHERE matched_planned_run_id = ?
            """,
            (planned_run_id,),
        )
        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def mark_planned_run_rescheduled(planned_run_id: int):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE planned_runs
            SET
                status = ?,
                manual_override = 1,
                override_reason = 'manuelt flyttet',
                matched_activity_id = NULL,
                matched_activity_date = NULL,
                matched_activity_name = NULL,
                actual_value = NULL,
                match_score = NULL,
                match_reason = NULL,
                evaluated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (STATUS_FLYTTET, planned_run_id),
        )
        conn.execute(
            """
            UPDATE activities
            SET matched_planned_run_id = NULL
            WHERE matched_planned_run_id = ?
            """,
            (planned_run_id,),
        )
        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def clear_planned_run_match(planned_run_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT matched_activity_id FROM planned_runs WHERE id = ?",
            (planned_run_id,),
        ).fetchone()

        conn.execute(
            """
            UPDATE planned_runs
            SET
                status = ?,
                manual_override = 1,
                override_reason = 'match fjernet manuelt',
                matched_activity_id = NULL,
                matched_activity_date = NULL,
                matched_activity_name = NULL,
                actual_value = NULL,
                match_score = NULL,
                match_reason = NULL,
                evaluated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (STATUS_PLANLAGT, planned_run_id),
        )

        if row and row["matched_activity_id"]:
            conn.execute(
                """
                UPDATE activities
                SET matched_planned_run_id = NULL
                WHERE id = ?
                """,
                (row["matched_activity_id"],),
            )

        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def match_activity_to_planned_run(planned_run_id: int, activity_id: int):
    conn = get_conn()
    try:
        activity = conn.execute(
            """
            SELECT *
            FROM activities
            WHERE id = ?
            """,
            (activity_id,),
        ).fetchone()

        planned = conn.execute(
            """
            SELECT *
            FROM planned_runs
            WHERE id = ?
            """,
            (planned_run_id,),
        ).fetchone()

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

        conn.execute(
            "UPDATE activities SET matched_planned_run_id = NULL WHERE matched_planned_run_id = ?",
            (planned_run_id,),
        )
        conn.execute(
            "UPDATE planned_runs SET matched_activity_id = NULL WHERE matched_activity_id = ?",
            (activity_id,),
        )

        conn.execute(
            """
            UPDATE planned_runs
            SET
                matched_activity_id = ?,
                matched_activity_date = ?,
                matched_activity_name = ?,
                actual_value = ?,
                status = ?,
                manual_override = 1,
                override_reason = 'match valgt manuelt',
                match_score = 0,
                match_reason = 'manuelt valgt match',
                evaluated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                activity_id,
                str(activity["start_date"])[:10],
                activity["name"],
                actual_value,
                status,
                planned_run_id,
            ),
        )

        conn.execute(
            """
            UPDATE activities
            SET matched_planned_run_id = ?, is_extra = 0
            WHERE id = ?
            """,
            (planned_run_id, activity_id),
        )

        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def update_planned_run(planned_run_id: int, data: dict):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE planned_runs
            SET
                planned_date = ?,
                session_type = ?,
                target_type = ?,
                target_value = ?,
                optional = ?,
                notes = ?,
                manual_override = 1,
                override_reason = 'manuelt redigeret',
                match_score = NULL,
                match_reason = NULL,
                evaluated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                data["planned_date"],
                data["session_type"],
                data["target_type"],
                data["target_value"],
                int(data.get("optional", False)),
                data.get("notes"),
                planned_run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return evaluate_and_sync()


def delete_planned_run(planned_run_id: int):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE activities
            SET matched_planned_run_id = NULL
            WHERE matched_planned_run_id = ?
            """,
            (planned_run_id,),
        )
        conn.execute(
            "DELETE FROM planned_runs WHERE id = ?",
            (planned_run_id,),
        )
        conn.commit()
    finally:
        conn.close()

    rebuild_activity_links()
    return {"deleted": planned_run_id}
