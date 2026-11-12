from __future__ import annotations

import json
import sqlite3


def upsert(conn: sqlite3.Connection, activity: dict) -> None:
    conn.execute(
        """
        INSERT INTO activities (
            id, name, sport_type, start_date, timezone_name, distance_m,
            moving_time_s, elapsed_time_s, total_elevation_gain, average_speed,
            max_speed, average_heartrate, max_heartrate, average_cadence,
            raw_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            sport_type = excluded.sport_type,
            start_date = excluded.start_date,
            timezone_name = excluded.timezone_name,
            distance_m = excluded.distance_m,
            moving_time_s = excluded.moving_time_s,
            elapsed_time_s = excluded.elapsed_time_s,
            total_elevation_gain = excluded.total_elevation_gain,
            average_speed = excluded.average_speed,
            max_speed = excluded.max_speed,
            average_heartrate = excluded.average_heartrate,
            max_heartrate = excluded.max_heartrate,
            average_cadence = excluded.average_cadence,
            raw_json = excluded.raw_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            activity["id"],
            activity.get("name"),
            activity.get("sport_type"),
            activity.get("start_date"),
            activity.get("timezone"),
            activity.get("distance"),
            activity.get("moving_time"),
            activity.get("elapsed_time"),
            activity.get("total_elevation_gain"),
            activity.get("average_speed"),
            activity.get("max_speed"),
            activity.get("average_heartrate"),
            activity.get("max_heartrate"),
            activity.get("average_cadence"),
            json.dumps(activity, ensure_ascii=False),
        ),
    )


def get(conn: sqlite3.Connection, activity_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()


def delete(conn: sqlite3.Connection, activity_id: int) -> int:
    conn.execute("DELETE FROM derived_metrics WHERE activity_id = ?", (activity_id,))
    return conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,)).rowcount


def list_runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """All runs, oldest first, every column."""
    return conn.execute(
        "SELECT * FROM activities WHERE sport_type = 'Run' ORDER BY start_date, id"
    ).fetchall()


def list_recent_runs(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, name, start_date, distance_m, moving_time_s,
               average_heartrate, is_extra, matched_planned_run_id
        FROM activities
        WHERE sport_type = 'Run'
        ORDER BY start_date DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_runs_since(conn: sqlite3.Connection, cutoff: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT start_date, name, distance_m, moving_time_s,
               average_heartrate, total_elevation_gain
        FROM activities
        WHERE sport_type = 'Run' AND start_date >= ?
        ORDER BY start_date
        """,
        (cutoff,),
    ).fetchall()


def list_runs_for_metrics(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, name, sport_type, start_date, distance_m, moving_time_s,
               average_heartrate, is_extra, matched_planned_run_id
        FROM activities
        WHERE sport_type = 'Run'
        ORDER BY start_date
        """
    ).fetchall()


# ---- plan links ------------------------------------------------------------

def reset_links(conn: sqlite3.Connection) -> None:
    """Forget every plan link and extra flag (used before re-matching)."""
    conn.execute("UPDATE activities SET matched_planned_run_id = NULL, is_extra = 0")


def mark_all_extra(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE activities SET matched_planned_run_id = NULL, is_extra = 1")


def link_from_planned_runs(conn: sqlite3.Connection) -> None:
    """Derive activity -> plan links from planned_runs.matched_activity_id."""
    conn.execute(
        """
        UPDATE activities
        SET
            matched_planned_run_id = (
                SELECT p.id FROM planned_runs p
                WHERE p.matched_activity_id = activities.id
                LIMIT 1
            ),
            is_extra = 0
        WHERE EXISTS (
            SELECT 1 FROM planned_runs p WHERE p.matched_activity_id = activities.id
        )
        """
    )


def set_matched_plan(
    conn: sqlite3.Connection, activity_id: int, plan_id: int, is_extra: int | None = None
) -> None:
    if is_extra is None:
        conn.execute(
            "UPDATE activities SET matched_planned_run_id = ? WHERE id = ?",
            (plan_id, activity_id),
        )
    else:
        conn.execute(
            "UPDATE activities SET matched_planned_run_id = ?, is_extra = ? WHERE id = ?",
            (plan_id, is_extra, activity_id),
        )


def clear_links_for_plan(conn: sqlite3.Connection, plan_id: int) -> None:
    conn.execute(
        "UPDATE activities SET matched_planned_run_id = NULL WHERE matched_planned_run_id = ?",
        (plan_id,),
    )


def clear_link_for_activity(conn: sqlite3.Connection, activity_id: int) -> None:
    conn.execute(
        "UPDATE activities SET matched_planned_run_id = NULL WHERE id = ?",
        (activity_id,),
    )


def refresh_extra_flags(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE activities
        SET is_extra = CASE WHEN matched_planned_run_id IS NULL THEN 1 ELSE 0 END
        WHERE sport_type = 'Run'
        """
    )


def count_link_mismatches(conn: sqlite3.Connection) -> int:
    return conn.execute(
        """
        SELECT COUNT(*)
        FROM activities a
        WHERE
            (a.matched_planned_run_id IS NULL AND EXISTS (
                SELECT 1 FROM planned_runs p WHERE p.matched_activity_id = a.id
            ))
            OR
            (a.matched_planned_run_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM planned_runs p WHERE p.id = a.matched_planned_run_id
            ))
        """
    ).fetchone()[0]
