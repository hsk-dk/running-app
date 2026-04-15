from __future__ import annotations

from datetime import datetime, timedelta
import sqlite3

import pandas as pd

from app.db import get_conn


STATUS_PLANLAGT = "planlagt"
STATUS_GENNEMFORT = "gennemført"
STATUS_FORKORTET = "forkortet"
STATUS_SPRUNGET_OVER = "sprunget over"
STATUS_FLYTTET = "flyttet"
STATUS_EKSTRA = "ekstra"


def _parse_dt(value: str) -> datetime:
    return pd.to_datetime(value, utc=True).tz_convert(None).to_pydatetime()


def _planned_dt(value: str) -> datetime:
    return pd.to_datetime(value).to_pydatetime()


def _compute_actual_value(planned_row: sqlite3.Row, activity_row: sqlite3.Row) -> float:
    target_type = planned_row["target_type"] or "time"
    if target_type == "distance":
        return float(activity_row["distance_m"] or 0.0) / 1000.0
    return float(activity_row["moving_time_s"] or 0.0) / 60.0


def _compute_ratio(target_value: float | None, actual_value: float) -> float:
    if not target_value or target_value <= 0:
        return 0.0
    return actual_value / float(target_value)


def _compute_status(target_value: float | None, actual_value: float) -> str:
    ratio = _compute_ratio(target_value, actual_value)
    if ratio >= 0.9:
        return STATUS_GENNEMFORT
    if ratio >= 0.5:
        return STATUS_FORKORTET
    return STATUS_SPRUNGET_OVER


def _reset_auto_matches(conn: sqlite3.Connection) -> None:
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
            evaluated_at = CURRENT_TIMESTAMP,
            status = CASE
                WHEN status IN (?, ?, ?, ?)
                THEN ?
                ELSE status
            END
        WHERE COALESCE(manual_override, 0) = 0
        """,
        (
            STATUS_GENNEMFORT,
            STATUS_FORKORTET,
            STATUS_SPRUNGET_OVER,
            STATUS_PLANLAGT,
            STATUS_PLANLAGT,
        ),
    )

    conn.execute(
        """
        UPDATE activities
        SET
            matched_planned_run_id = NULL,
            is_extra = 0
        """
    )


def _candidate_score(
    planned_row: sqlite3.Row,
    activity_row: sqlite3.Row,
    planned_date: datetime,
    activity_date: datetime,
) -> tuple[tuple[float, float, int, str, int], float, str]:
    day_diff = abs((activity_date.date() - planned_date.date()).days)

    target_value = planned_row["target_value"]
    actual_value = _compute_actual_value(planned_row, activity_row)

    if target_value is not None and float(target_value) > 0:
        value_diff = abs(actual_value - float(target_value))
    else:
        value_diff = 9999.0

    session_type = (planned_row["session_type"] or "").lower()
    long_penalty = 0
    long_reason = ""

    if session_type == "long":
        if planned_row["target_type"] == "distance":
            activity_amount = float(activity_row["distance_m"] or 0.0) / 1000.0
        else:
            activity_amount = float(activity_row["moving_time_s"] or 0.0) / 60.0

        target_amount = float(target_value or 0.0)
        if target_amount > 0 and activity_amount < (target_amount * 0.8):
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
        reason = (
            f"Valgt pga. datoafstand {day_diff} dag(e) og målafvigelse "
            f"{round(value_diff, 2)} "
            f"{'km' if (planned_row['target_type'] == 'distance') else 'min'}"
            f"{long_reason}"
         )
    else:
        reason = f"datoafstand={day_diff} dag(e), intet måltal{long_reason}"

    return score_tuple, flat_score, reason

def evaluate_planned_runs(tolerance_days: int = 1):
    conn = get_conn()
    try:
        _reset_auto_matches(conn)

        planned_rows = conn.execute(
            """
            SELECT *
            FROM planned_runs
            ORDER BY planned_date, id
            """
        ).fetchall()

        activity_rows = conn.execute(
            """
            SELECT *
            FROM activities
            WHERE sport_type = 'Run'
            ORDER BY start_date, id
            """
        ).fetchall()

        used_activity_ids: set[int] = set()

        for p in planned_rows:
            if p["manual_override"] and p["matched_activity_id"]:
                used_activity_ids.add(int(p["matched_activity_id"]))

        for planned in planned_rows:
            if planned["manual_override"]:
                continue

            planned_date = _planned_dt(planned["planned_date"])
            window_start = planned_date - timedelta(days=tolerance_days)
            window_end = planned_date + timedelta(days=tolerance_days)

            candidates = []
            for activity in activity_rows:
                activity_id = int(activity["id"])
                if activity_id in used_activity_ids:
                    continue

                activity_date = _parse_dt(activity["start_date"])
                if window_start <= activity_date <= window_end:
                    score_tuple, flat_score, reason = _candidate_score(
                        planned, activity, planned_date, activity_date
                    )
                    candidates.append((activity, score_tuple, flat_score, reason))

            if not candidates:
                now = datetime.now()
                window_deadline = planned_date + timedelta(days=tolerance_days)

                status = (
                    STATUS_SPRUNGET_OVER
                    if now > window_deadline
                    else STATUS_PLANLAGT
                )

                conn.execute(
                    """
                    UPDATE planned_runs
                    SET
                        status = ?,
                        evaluated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (status, planned["id"]),
                )
                continue

            candidates.sort(key=lambda item: item[1])
            best, _, best_flat_score, best_reason = candidates[0]

            used_activity_ids.add(int(best["id"]))

            actual_value = _compute_actual_value(planned, best)
            status = _compute_status(planned["target_value"], actual_value)

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
                 WHERE id = ?
                 """,
                 (
                     best["id"],
                     str(best["start_date"])[:10],
                     best["name"],
                     actual_value,
                     status,
                     best_flat_score,
                     best_reason,
                     planned["id"],
                 ),
              )

            conn.execute(
                """
                UPDATE activities
                SET matched_planned_run_id = ?
                WHERE id = ?
                """,
                (planned["id"], best["id"]),
            )

        conn.execute(
            """
            UPDATE activities
            SET is_extra = CASE
                WHEN matched_planned_run_id IS NULL THEN 1
                ELSE 0
            END
            WHERE sport_type = 'Run'
            """
        )

        conn.commit()
        return {"updated": len(planned_rows)}
    finally:
        conn.close()


def get_weekly_consistency(tolerance_days: int = 1):
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            """
            SELECT planned_date, mandatory, status
            FROM planned_runs
            ORDER BY planned_date
            """,
            conn,
        )

        if df.empty:
            return []

        now = datetime.now()
        df["planned_date"] = pd.to_datetime(df["planned_date"])
        df["window_end"] = df["planned_date"] + pd.to_timedelta(tolerance_days, unit="D")
        df["counts_now"] = df.apply(
            lambda row: row["status"] != STATUS_PLANLAGT or row["window_end"] < pd.Timestamp(now),
            axis=1,
        )

        iso = df["planned_date"].dt.isocalendar()
        df["week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)

        mandatory = df[df["mandatory"] == 1].copy()
        rows = []

        for week, g in mandatory.groupby("week"):
            relevant = g[g["counts_now"] == True]

            if relevant.empty:
                score = "Grøn"
                completed = 0
                shortened = 0
                total = 0
            else:
                completed = int((relevant["status"] == STATUS_GENNEMFORT).sum())
                shortened = int((relevant["status"] == STATUS_FORKORTET).sum())
                total = int(len(relevant))

                if total > 0 and completed == total:
                    score = "Grøn"
                elif completed + shortened > 0:
                    score = "Gul"
                else:
                    score = "Rød"

            rows.append(
                {
                    "week": week,
                    "mandatory_runs": int(len(g)),
                    "relevant_runs": total,
                    "completed": completed,
                    "shortened": shortened,
                    "score": score,
                }
            )

        return rows
    finally:
        conn.close()
