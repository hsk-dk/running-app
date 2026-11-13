from __future__ import annotations

import sqlite3


def list_all(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM planned_runs WHERE user_id = ? ORDER BY planned_date, id", (user_id,)
    ).fetchall()


def get(conn: sqlite3.Connection, user_id: int, plan_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM planned_runs WHERE id = ? AND user_id = ?", (plan_id, user_id)
    ).fetchone()


def list_between(conn: sqlite3.Connection, user_id: int, start: str, end: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT planned_date, session_type, target_type, target_value,
               mandatory, status, notes
        FROM planned_runs
        WHERE user_id = ? AND planned_date BETWEEN ? AND ?
        ORDER BY planned_date
        """,
        (user_id, start, end),
    ).fetchall()


def insert(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    planned_date,
    session_type,
    target_minutes,
    optional: int,
    notes,
    status: str,
    target_type,
    target_value,
    mandatory: int,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO planned_runs (
            planned_date, session_type, target_minutes, optional, notes, status,
            target_type, target_value, mandatory, manual_override, match_score, match_reason, user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?)
        """,
        (
            planned_date, session_type, target_minutes, optional, notes, status,
            target_type, target_value, mandatory, user_id,
        ),
    )
    return cur.lastrowid


def update_from_edit(
    conn: sqlite3.Connection,
    user_id: int,
    plan_id: int,
    *,
    planned_date,
    session_type,
    target_type,
    target_value,
    optional: int,
    notes,
) -> None:
    # `mandatory` is the source of truth; `optional` is kept in sync for old readers.
    conn.execute(
        """
        UPDATE planned_runs
        SET
            planned_date = ?,
            session_type = ?,
            target_type = ?,
            target_value = ?,
            optional = ?,
            mandatory = ?,
            notes = ?,
            manual_override = 1,
            override_reason = 'manuelt redigeret',
            match_score = NULL,
            match_reason = NULL,
            evaluated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (planned_date, session_type, target_type, target_value, optional, int(not optional), notes, plan_id, user_id),
    )


def delete(conn: sqlite3.Connection, user_id: int, plan_id: int) -> None:
    conn.execute("DELETE FROM planned_runs WHERE id = ? AND user_id = ?", (plan_id, user_id))


def set_manual_status(conn: sqlite3.Connection, user_id: int, plan_id: int, status: str, reason: str) -> None:
    """Manual override that also drops any match (skip / reschedule / clear)."""
    conn.execute(
        """
        UPDATE planned_runs
        SET
            status = ?,
            manual_override = 1,
            override_reason = ?,
            matched_activity_id = NULL,
            matched_activity_date = NULL,
            matched_activity_name = NULL,
            actual_value = NULL,
            match_score = NULL,
            match_reason = NULL,
            evaluated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (status, reason, plan_id, user_id),
    )


def set_manual_match(
    conn: sqlite3.Connection,
    user_id: int,
    plan_id: int,
    *,
    activity_id: int,
    activity_date: str,
    activity_name,
    actual_value: float,
    status: str,
) -> None:
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
        WHERE id = ? AND user_id = ?
        """,
        (activity_id, activity_date, activity_name, actual_value, status, plan_id, user_id),
    )


def set_auto_match(
    conn: sqlite3.Connection,
    user_id: int,
    plan_id: int,
    *,
    activity_id: int,
    activity_date: str,
    activity_name,
    actual_value: float,
    status: str,
    score: float,
    reason: str,
) -> None:
    conn.execute(
        """
        UPDATE planned_runs
        SET
            matched_activity_id = ?,
            matched_activity_date = ?,
            matched_activity_name = ?,
            actual_value = ?,
            status = ?,
            match_score = ?,
            match_reason = ?,
            evaluated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (activity_id, activity_date, activity_name, actual_value, status, score, reason, plan_id, user_id),
    )


def set_status(conn: sqlite3.Connection, user_id: int, plan_id: int, status: str) -> None:
    conn.execute(
        "UPDATE planned_runs SET status = ?, evaluated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
        (status, plan_id, user_id),
    )


def reset_auto_matches(
    conn: sqlite3.Connection, user_id: int, resettable_statuses: tuple[str, ...], planned_status: str
) -> None:
    """Drop matches on every non-manual plan of the user; evaluated statuses go back to 'planned'."""
    placeholders = ", ".join("?" for _ in resettable_statuses)
    conn.execute(
        f"""
        UPDATE planned_runs
        SET
            matched_activity_id = NULL,
            matched_activity_date = NULL,
            matched_activity_name = NULL,
            actual_value = NULL,
            match_score = NULL,
            match_reason = NULL,
            evaluated_at = CURRENT_TIMESTAMP,
            status = CASE WHEN status IN ({placeholders}) THEN ? ELSE status END
        WHERE user_id = ? AND COALESCE(manual_override, 0) = 0
        """,  # placeholders are only "?" markers, never user data
        (*resettable_statuses, planned_status, user_id),
    )


def unmatch_activity(conn: sqlite3.Connection, user_id: int, activity_id: int) -> None:
    """Remove the activity from any plan that points at it, keeping the plan."""
    conn.execute(
        """
        UPDATE planned_runs
        SET
            matched_activity_id = NULL,
            matched_activity_date = NULL,
            matched_activity_name = NULL,
            actual_value = NULL,
            match_score = NULL,
            match_reason = NULL,
            evaluated_at = CURRENT_TIMESTAMP
        WHERE matched_activity_id = ? AND user_id = ?
        """,
        (activity_id, user_id),
    )


def clear_matched_activity_id(conn: sqlite3.Connection, user_id: int, activity_id: int) -> None:
    """Minimal variant used when re-assigning an activity manually."""
    conn.execute(
        "UPDATE planned_runs SET matched_activity_id = NULL WHERE matched_activity_id = ? AND user_id = ?",
        (activity_id, user_id),
    )
