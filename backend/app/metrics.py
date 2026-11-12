from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.db import get_conn
from app.domain import timeutil, weekly
from app.domain.runs import is_mandatory
from app.domain.statuses import STATUS_PLANLAGT
from app.repositories import activities as activity_repo
from app.repositories import planned_runs as plan_repo


def _safe_pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    current = float(current or 0)
    previous = float(previous or 0)
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _month_stats(rows: list) -> tuple[int, float, float | None]:
    runs = len(rows)
    km = round(sum(float(r["distance_m"] or 0) for r in rows) / 1000.0, 2)
    hrs = [float(r["average_heartrate"]) for r in rows if r["average_heartrate"] is not None]
    avg_hr = round(sum(hrs) / len(hrs), 1) if hrs else None
    return runs, km, avg_hr


def _current_week_summary(conn, today: date) -> dict:
    current_week = weekly.iso_week_key(today)
    plans = []
    for row in plan_repo.list_all(conn):
        if not is_mandatory(row):
            continue
        try:
            planned_date = timeutil.parse_planned_date(row["planned_date"])
        except ValueError:
            continue
        if weekly.iso_week_key(planned_date) == current_week:
            plans.append((planned_date, row["status"] or STATUS_PLANLAGT))
    return weekly.summarize(plans, today, tolerance_days=1)


def get_summary():
    conn = get_conn()
    try:
        today = timeutil.today()
        month = (today.year, today.month)
        prev_month = _previous_month(*month)

        by_month: dict[tuple[int, int], list] = defaultdict(list)
        for row in activity_repo.list_runs_for_metrics(conn):
            run_date = timeutil.activity_local_date(row)
            if run_date is not None:
                by_month[(run_date.year, run_date.month)].append(row)

        current_runs, current_km, current_avg_hr = _month_stats(by_month.get(month, []))
        prev_runs, prev_km, prev_avg_hr = _month_stats(by_month.get(prev_month, []))

        week = _current_week_summary(conn, today)
        adherence = weekly.adherence_pct(week)

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
            "adherence_pct_current_week": adherence,
            "current_week_completed": week["completed"],
            "current_week_shortened": week["shortened"],
            "current_week_relevant": week["relevant_runs"],
            "current_week_awaiting": week["awaiting"],
            # backward compatibility
            "total_runs": current_runs,
            "total_km": current_km,
            "avg_hr": current_avg_hr,
            "adherence_pct": adherence,
        }
    finally:
        conn.close()


def get_monthly_volume():
    conn = get_conn()
    try:
        meters_by_month: dict[str, float] = defaultdict(float)
        for row in activity_repo.list_runs_for_metrics(conn):
            run_date = timeutil.activity_local_date(row)
            if run_date is not None:
                meters_by_month[run_date.strftime("%Y-%m")] += float(row["distance_m"] or 0)

        return [
            {"month": month, "km": round(meters / 1000.0, 2)}
            for month, meters in sorted(meters_by_month.items())
        ]
    finally:
        conn.close()


def get_activities(limit: int = 100):
    conn = get_conn()
    try:
        data = []
        for row in activity_repo.list_recent_runs(conn, limit):
            run_date = timeutil.activity_local_date(row)
            data.append(
                {
                    "id": row["id"],
                    "date": run_date.isoformat() if run_date else None,
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
