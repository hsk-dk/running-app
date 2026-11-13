from __future__ import annotations

import json
import sqlite3


def upsert(conn: sqlite3.Connection, user_id: int, activity: dict, source: str = "strava", source_id: str | None = None) -> None:
    """Insert or update one of the user's activities. An activity id that belongs to another user is left alone."""
    conn.execute(
        """
        INSERT INTO activities (
            id, name, sport_type, start_date, start_date_local, timezone_name, distance_m,
            moving_time_s, elapsed_time_s, total_elevation_gain, average_speed,
            max_speed, average_heartrate, max_heartrate, average_cadence,
            raw_json, user_id, source, source_id, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            sport_type = excluded.sport_type,
            start_date = excluded.start_date,
            start_date_local = excluded.start_date_local,
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
        WHERE activities.user_id = excluded.user_id
        """,
        (
            activity["id"],
            activity.get("name"),
            activity.get("sport_type"),
            activity.get("start_date"),
            activity.get("start_date_local"),
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
            user_id,
            source,
            source_id if source_id is not None else str(activity["id"]),
        ),
    )


def find_near(conn: sqlite3.Connection, user_id: int, start_utc: str, window_s: int = 120, source: str | None = None) -> sqlite3.Row | None:
    """A run of the user's that started within `window_s` seconds of `start_utc` (the same run from another source).

    With `source`, only runs from that source count."""
    sql = "SELECT * FROM activities WHERE user_id = ? AND sport_type = 'Run' AND start_date IS NOT NULL AND ABS(julianday(start_date) - julianday(?)) * 86400 <= ?"
    args: list = [user_id, start_utc, window_s]
    if source is not None:
        sql += " AND source = ?"
        args.append(source)
    return conn.execute(sql + " ORDER BY ABS(julianday(start_date) - julianday(?)) LIMIT 1", args + [start_utc]).fetchone()


def get(conn: sqlite3.Connection, user_id: int, activity_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM activities WHERE id = ? AND user_id = ?", (activity_id, user_id)
    ).fetchone()


def get_splits_json(conn: sqlite3.Connection, user_id: int, activity_id: int) -> str | None:
    row = conn.execute(
        "SELECT splits_json FROM activities WHERE id = ? AND user_id = ?", (activity_id, user_id)
    ).fetchone()
    return row["splits_json"] if row else None


def set_splits_json(conn: sqlite3.Connection, user_id: int, activity_id: int, splits_json: str) -> None:
    conn.execute(
        "UPDATE activities SET splits_json = ? WHERE id = ? AND user_id = ?", (splits_json, activity_id, user_id)
    )


def delete(conn: sqlite3.Connection, user_id: int, activity_id: int) -> int:
    return conn.execute(
        "DELETE FROM activities WHERE id = ? AND user_id = ?", (activity_id, user_id)
    ).rowcount


def list_runs(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """All of the user's runs, oldest first, every column."""
    return conn.execute(
        "SELECT * FROM activities WHERE user_id = ? AND sport_type = 'Run' ORDER BY start_date, id",
        (user_id,),
    ).fetchall()


def list_recent_runs(conn: sqlite3.Connection, user_id: int, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, name, start_date, start_date_local, distance_m, moving_time_s,
               average_heartrate, is_extra, matched_planned_run_id
        FROM activities
        WHERE user_id = ? AND sport_type = 'Run'
        ORDER BY start_date DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()


def list_runs_since(conn: sqlite3.Connection, user_id: int, cutoff: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT start_date, start_date_local, name, distance_m, moving_time_s,
               average_heartrate, total_elevation_gain
        FROM activities
        WHERE user_id = ? AND sport_type = 'Run' AND start_date >= ?
        ORDER BY start_date
        """,
        (user_id, cutoff),
    ).fetchall()


def list_runs_for_metrics(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, name, sport_type, start_date, start_date_local, distance_m, moving_time_s,
               average_heartrate, is_extra, matched_planned_run_id
        FROM activities
        WHERE user_id = ? AND sport_type = 'Run'
        ORDER BY start_date
        """,
        (user_id,),
    ).fetchall()


# ---- plan links ------------------------------------------------------------

def reset_links(conn: sqlite3.Connection, user_id: int) -> None:
    """Forget every plan link and extra flag of the user (used before re-matching)."""
    conn.execute(
        "UPDATE activities SET matched_planned_run_id = NULL, is_extra = 0 WHERE user_id = ?",
        (user_id,),
    )


def mark_all_extra(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute(
        "UPDATE activities SET matched_planned_run_id = NULL, is_extra = 1 WHERE user_id = ?",
        (user_id,),
    )


def link_from_planned_runs(conn: sqlite3.Connection, user_id: int) -> None:
    """Derive activity -> plan links from planned_runs.matched_activity_id."""
    conn.execute(
        """
        UPDATE activities
        SET
            matched_planned_run_id = (
                SELECT p.id FROM planned_runs p
                WHERE p.matched_activity_id = activities.id AND p.user_id = activities.user_id
                LIMIT 1
            ),
            is_extra = 0
        WHERE activities.user_id = ? AND EXISTS (
            SELECT 1 FROM planned_runs p
            WHERE p.matched_activity_id = activities.id AND p.user_id = activities.user_id
        )
        """,
        (user_id,),
    )


def set_matched_plan(
    conn: sqlite3.Connection, user_id: int, activity_id: int, plan_id: int, is_extra: int | None = None
) -> None:
    if is_extra is None:
        conn.execute(
            "UPDATE activities SET matched_planned_run_id = ? WHERE id = ? AND user_id = ?",
            (plan_id, activity_id, user_id),
        )
    else:
        conn.execute(
            "UPDATE activities SET matched_planned_run_id = ?, is_extra = ? WHERE id = ? AND user_id = ?",
            (plan_id, is_extra, activity_id, user_id),
        )


def clear_links_for_plan(conn: sqlite3.Connection, user_id: int, plan_id: int) -> None:
    conn.execute(
        "UPDATE activities SET matched_planned_run_id = NULL WHERE matched_planned_run_id = ? AND user_id = ?",
        (plan_id, user_id),
    )


def clear_link_for_activity(conn: sqlite3.Connection, user_id: int, activity_id: int) -> None:
    conn.execute(
        "UPDATE activities SET matched_planned_run_id = NULL WHERE id = ? AND user_id = ?",
        (activity_id, user_id),
    )


def refresh_extra_flags(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute(
        """
        UPDATE activities
        SET is_extra = CASE WHEN matched_planned_run_id IS NULL THEN 1 ELSE 0 END
        WHERE user_id = ? AND sport_type = 'Run'
        """,
        (user_id,),
    )


def count_link_mismatches(conn: sqlite3.Connection, user_id: int | None = None) -> int:
    """Activities whose link disagrees with the plans. user_id=None checks every user."""
    scope = "" if user_id is None else "AND a.user_id = ?"
    params = () if user_id is None else (user_id,)
    return conn.execute(
        f"""
        SELECT COUNT(*)
        FROM activities a
        WHERE (
            (a.matched_planned_run_id IS NULL AND EXISTS (
                SELECT 1 FROM planned_runs p WHERE p.matched_activity_id = a.id
            ))
            OR
            (a.matched_planned_run_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM planned_runs p WHERE p.id = a.matched_planned_run_id
            ))
        ) {scope}
        """,  # scope is a fixed literal, never user input
        params,
    ).fetchone()[0]


def find_near_local(conn: sqlite3.Connection, user_id: int, start_local: str, window_s: int = 300) -> sqlite3.Row | None:
    """A run of the user's whose local start time is within `window_s` seconds of `start_local` (wall-clock time)."""
    return conn.execute(
        "SELECT * FROM activities WHERE user_id = ? AND sport_type = 'Run' AND start_date_local IS NOT NULL "
        "AND ABS(julianday(start_date_local) - julianday(?)) * 86400 <= ? "
        "ORDER BY ABS(julianday(start_date_local) - julianday(?)) LIMIT 1",
        (user_id, start_local, window_s, start_local),
    ).fetchone()


def set_name_if_empty(conn: sqlite3.Connection, user_id: int, activity_id: int, name: str) -> bool:
    """Give a run a name, but never replace one that already has a name."""
    return conn.execute(
        "UPDATE activities SET name = ? WHERE id = ? AND user_id = ? AND (name IS NULL OR TRIM(name) = '')",
        (name, activity_id, user_id),
    ).rowcount > 0


def list_with_raw(conn: sqlite3.Connection, user_id: int, limit: int) -> list[sqlite3.Row]:
    """The user's newest runs with the stored source data (used to pull out each run's route)."""
    return conn.execute(
        "SELECT id, start_date, start_date_local, distance_m, raw_json, route_polyline FROM activities "
        "WHERE user_id = ? AND sport_type = 'Run' ORDER BY start_date DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


# ---- Garmin: link to the Garmin activity and keep what its FIT file says ---------------------------------

def set_garmin_id(conn: sqlite3.Connection, user_id: int, activity_id: int, garmin_id: int) -> None:
    conn.execute("UPDATE activities SET garmin_id = ? WHERE id = ? AND user_id = ?", (garmin_id, activity_id, user_id))


def set_fit_result(
    conn: sqlite3.Connection, user_id: int, activity_id: int, *, status: str,
    route: str | None = None, profile_json: str | None = None, laps_json: str | None = None, splits_json: str | None = None,
) -> None:
    """Save what the FIT file said. The route only fills a gap: a run that already has one keeps it."""
    conn.execute(
        """
        UPDATE activities SET fit_status = ?, profile_json = ?, laps_json = ?,
            route_polyline = COALESCE(route_polyline, ?),
            splits_json = COALESCE(?, splits_json)
        WHERE id = ? AND user_id = ?
        """,
        (status, profile_json, laps_json, route, splits_json, activity_id, user_id),
    )


def has_run_near_date(conn: sqlite3.Connection, user_id: int, day: str, days: int = 1) -> bool:
    """Is there a run on that local calendar day, or within `days` of it?"""
    return conn.execute(
        """
        SELECT 1 FROM activities
        WHERE user_id = ? AND sport_type = 'Run'
          AND date(COALESCE(substr(start_date_local, 1, 10), substr(start_date, 1, 10)))
              BETWEEN date(?, ?) AND date(?, ?)
        LIMIT 1
        """,
        (user_id, day, f"-{days} day", day, f"+{days} day"),
    ).fetchone() is not None
