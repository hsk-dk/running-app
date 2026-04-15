from __future__ import annotations

from datetime import datetime, timedelta
import sqlite3

import pandas as pd

from app.db import get_conn


STATUS_PLANLAGT = "planlagt"
STATUS_GENNEMFORT = "gennemført"
STATUS_FORKORTET = "forkortet"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return pd.to_datetime(value, utc=True).tz_convert(None).to_pydatetime()
    except Exception:
        try:
            return pd.to_datetime(value).to_pydatetime()
        except Exception:
            return None


def _month_bounds(now: datetime) -> tuple[datetime, datetime, datetime, datetime]:
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = month_start - timedelta(seconds=1)
    prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month_start = (month_start + pd.offsets.MonthBegin(1)).to_pydatetime()
    return month_start, next_month_start, prev_month_start, month_start


def _iso_week_key(value: datetime) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _is_awaiting(planned_date: datetime, tolerance_days: int = 1) -> bool:
    deadline = planned_date + timedelta(days=tolerance_days)
    return datetime.now() <= deadline


def _safe_pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    current = float(current or 0)
    previous = float(previous or 0)
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def rebuild_metrics():
    # Placeholder for MVP compatibility.
    return {"ok": True}


def get_summary():
    conn = get_conn()
    try:
        now = datetime.now()
        month_start, next_month_start, prev_month_start, prev_month_end_exclusive = _month_bounds(now)

        activities_df = pd.read_sql_query(
            """
            SELECT
                id,
                name,
                sport_type,
                start_date,
                distance_m,
                moving_time_s,
                average_heartrate,
                is_extra,
                matched_planned_run_id
            FROM activities
            WHERE sport_type = 'Run'
            ORDER BY start_date
            """,
            conn,
        )

        planned_df = pd.read_sql_query(
            """
            SELECT
                id,
                planned_date,
                status,
                optional,
                mandatory
            FROM planned_runs
            ORDER BY planned_date
            """,
            conn,
        )

        if activities_df.empty:
            current_runs = 0
            prev_runs = 0
            current_km = 0.0
            prev_km = 0.0
            current_avg_hr = None
            prev_avg_hr = None
        else:
            activities_df["start_dt"] = pd.to_datetime(activities_df["start_date"], utc=True, errors="coerce")
            activities_df["start_dt"] = activities_df["start_dt"].dt.tz_convert(None)

            current_mask = (activities_df["start_dt"] >= month_start) & (activities_df["start_dt"] < next_month_start)
            prev_mask = (activities_df["start_dt"] >= prev_month_start) & (activities_df["start_dt"] < prev_month_end_exclusive)

            current_df = activities_df[current_mask].copy()
            prev_df = activities_df[prev_mask].copy()

            current_runs = int(len(current_df))
            prev_runs = int(len(prev_df))

            current_km = round(float(current_df["distance_m"].fillna(0).sum()) / 1000.0, 2)
            prev_km = round(float(prev_df["distance_m"].fillna(0).sum()) / 1000.0, 2)

            current_hr_series = current_df["average_heartrate"].dropna()
            prev_hr_series = prev_df["average_heartrate"].dropna()

            current_avg_hr = round(float(current_hr_series.mean()), 1) if not current_hr_series.empty else None
            prev_avg_hr = round(float(prev_hr_series.mean()), 1) if not prev_hr_series.empty else None

        current_week_key = _iso_week_key(now)

        if planned_df.empty:
            adherence_pct_current_week = 0
            current_week_completed = 0
            current_week_relevant = 0
            current_week_awaiting = 0
        else:
            planned_df["planned_dt"] = pd.to_datetime(planned_df["planned_date"], errors="coerce")
            planned_df["week_key"] = planned_df["planned_dt"].apply(
                lambda x: _iso_week_key(x.to_pydatetime()) if pd.notnull(x) else ""
            )

            week_df = planned_df[planned_df["week_key"] == current_week_key].copy()

            if "optional" in week_df.columns:
                mandatory_df = week_df[week_df["optional"].fillna(0) != 1].copy()
            elif "mandatory" in week_df.columns:
                mandatory_df = week_df[week_df["mandatory"].fillna(1) == 1].copy()
            else:
                mandatory_df = week_df.copy()

            def counts_now(row) -> bool:
                planned_dt = row["planned_dt"]
                if pd.isnull(planned_dt):
                    return False
                if row["status"] != STATUS_PLANLAGT:
                    return True
                return not _is_awaiting(planned_dt.to_pydatetime(), tolerance_days=1)

            mandatory_df["counts_now"] = mandatory_df.apply(counts_now, axis=1)

            relevant_df = mandatory_df[mandatory_df["counts_now"] == True].copy()
            current_week_completed = int((relevant_df["status"] == STATUS_GENNEMFORT).sum())
            current_week_relevant = int(len(relevant_df))
            current_week_awaiting = int(
                ((mandatory_df["status"] == STATUS_PLANLAGT) & (mandatory_df["counts_now"] == False)).sum()
            )

            adherence_pct_current_week = (
                int(round((current_week_completed / current_week_relevant) * 100))
                if current_week_relevant > 0
                else 0
            )

        return {
            "runs_this_month": current_runs,
            "runs_prev_month": prev_runs,
            "runs_change_pct": _safe_pct_change(current_runs, prev_runs),
            "km_this_month": current_km,
            "km_prev_month": prev_km,
            "km_change_pct": _safe_pct_change(current_km, prev_km),
            "avg_hr_this_month": current_avg_hr,
            "avg_hr_prev_month": prev_avg_hr,
            "avg_hr_change": (
                round((current_avg_hr - prev_avg_hr), 1)
                if current_avg_hr is not None and prev_avg_hr is not None
                else None
            ),
            "adherence_pct_current_week": adherence_pct_current_week,
            "current_week_completed": current_week_completed,
            "current_week_relevant": current_week_relevant,
            "current_week_awaiting": current_week_awaiting,
            # backward compatibility
            "total_runs": current_runs,
            "total_km": current_km,
            "avg_hr": current_avg_hr,
            "adherence_pct": adherence_pct_current_week,
        }
    finally:
        conn.close()


def get_monthly_volume():
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            """
            SELECT
                start_date,
                distance_m
            FROM activities
            WHERE sport_type = 'Run'
            ORDER BY start_date
            """,
            conn,
        )

        if df.empty:
            return []

        df["start_dt"] = pd.to_datetime(df["start_date"], utc=True, errors="coerce")
        df["start_dt"] = df["start_dt"].dt.tz_convert(None)
        df["month"] = df["start_dt"].dt.strftime("%Y-%m")
        result = (
            df.groupby("month", as_index=False)["distance_m"]
            .sum()
            .assign(km=lambda x: (x["distance_m"] / 1000.0).round(2))
        )

        return result[["month", "km"]].to_dict(orient="records")
    finally:
        conn.close()


def get_activities(limit: int = 100):
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                name,
                start_date,
                distance_m,
                moving_time_s,
                average_heartrate,
                is_extra,
                matched_planned_run_id
            FROM activities
            WHERE sport_type = 'Run'
            ORDER BY start_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        data = []
        for row in rows:
            start_dt = _parse_dt(row["start_date"])
            data.append(
                {
                    "id": row["id"],
                    "date": start_dt.strftime("%Y-%m-%d") if start_dt else None,
                    "name": row["name"],
                    "distance_km": round(float(row["distance_m"] or 0) / 1000.0, 2),
                    "duration_min": round(float(row["moving_time_s"] or 0) / 60.0, 1),
                    "avg_hr": round(float(row["average_heartrate"]), 1) if row["average_heartrate"] is not None else None,
                    "is_extra": bool(row["is_extra"]),
                    "matched_planned_run_id": row["matched_planned_run_id"],
                }
            )
        return data
    finally:
        conn.close()
