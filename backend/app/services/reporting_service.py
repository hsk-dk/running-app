from __future__ import annotations

import json
from collections import defaultdict
from datetime import date

from app.db import get_conn
from app.errors import NotFoundError
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


def _current_week_summary(conn, user_id: int, today: date) -> dict:
    current_week = weekly.iso_week_key(today)
    plans = []
    for row in plan_repo.list_all(conn, user_id):
        if not is_mandatory(row):
            continue
        try:
            planned_date = timeutil.parse_planned_date(row["planned_date"])
        except ValueError:
            continue
        if weekly.iso_week_key(planned_date) == current_week:
            plans.append((planned_date, row["status"] or STATUS_PLANLAGT))
    return weekly.summarize(plans, today, tolerance_days=1)


def summary(user_id: int):
    conn = get_conn()
    try:
        today = timeutil.today()
        month = (today.year, today.month)
        prev_month = _previous_month(*month)

        by_month: dict[tuple[int, int], list] = defaultdict(list)
        for row in activity_repo.list_runs_for_metrics(conn, user_id):
            run_date = timeutil.activity_local_date(row)
            if run_date is not None:
                by_month[(run_date.year, run_date.month)].append(row)

        current_runs, current_km, current_avg_hr = _month_stats(by_month.get(month, []))
        prev_runs, prev_km, prev_avg_hr = _month_stats(by_month.get(prev_month, []))

        week = _current_week_summary(conn, user_id, today)
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


def monthly_volume(user_id: int):
    conn = get_conn()
    try:
        meters_by_month: dict[str, float] = defaultdict(float)
        for row in activity_repo.list_runs_for_metrics(conn, user_id):
            run_date = timeutil.activity_local_date(row)
            if run_date is not None:
                meters_by_month[run_date.strftime("%Y-%m")] += float(row["distance_m"] or 0)

        return [
            {"month": month, "km": round(meters / 1000.0, 2)}
            for month, meters in sorted(meters_by_month.items())
        ]
    finally:
        conn.close()


def list_activities(user_id: int, limit: int = 100):
    conn = get_conn()
    try:
        data = []
        for row in activity_repo.list_recent_runs(conn, user_id, limit):
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


def _route_of(raw_json: str | None) -> str | None:
    """The simplified route stored with older runs from Strava (absent for treadmill runs)."""
    try:
        raw = json.loads(raw_json or "{}")
    except (TypeError, ValueError):
        return None
    summary_map = raw.get("map") if isinstance(raw, dict) else None
    route = summary_map.get("summary_polyline") if isinstance(summary_map, dict) else None
    return route or None


def routes(user_id: int, limit: int = 400):
    """Every route the user has, newest first, as small records for the route poster. Runs without GPS are left out."""
    conn = get_conn()
    try:
        rows = activity_repo.list_with_raw(conn, user_id, limit)
    finally:
        conn.close()
    out = []
    for row in rows:
        route = row["route_polyline"] or _route_of(row["raw_json"])
        if not route:
            continue
        day = timeutil.activity_local_date(row)
        out.append(
            {
                "id": row["id"],
                "date": day.isoformat() if day else None,
                "distance_km": round(float(row["distance_m"] or 0) / 1000.0, 2),
                "route": route,
            }
        )
    return out


def get_activity(user_id: int, activity_id: int):
    conn = get_conn()
    try:
        row = activity_repo.get(conn, user_id, activity_id)
        if row is None or row["sport_type"] != "Run":
            raise NotFoundError(f"Activity {activity_id} not found")

        run_date = timeutil.activity_local_date(row)
        distance_m = float(row["distance_m"] or 0)
        moving_s = float(row["moving_time_s"] or 0)
        local = row["start_date_local"]
        return {
            "id": row["id"],
            "date": run_date.isoformat() if run_date else None,
            "name": row["name"],
            "distance_km": round(distance_m / 1000.0, 2),
            "duration_min": round(moving_s / 60.0, 1),
            "avg_hr": round(float(row["average_heartrate"]), 1) if row["average_heartrate"] is not None else None,
            "is_extra": bool(row["is_extra"]),
            "matched_planned_run_id": row["matched_planned_run_id"],
            "start_time_local": str(local) if local else None,
            "elevation_gain_m": round(float(row["total_elevation_gain"]), 0) if row["total_elevation_gain"] is not None else None,
            "avg_pace_s_per_km": round(moving_s / (distance_m / 1000.0), 1) if distance_m > 0 and moving_s > 0 else None,
            "max_hr": round(float(row["max_heartrate"]), 1) if row["max_heartrate"] is not None else None,
            "route": row["route_polyline"] or _route_of(row["raw_json"]),
        }
    finally:
        conn.close()


def weekly_consistency(user_id: int, tolerance_days: int = 1):
    conn = get_conn()
    try:
        weeks: dict[str, list[tuple[date, str]]] = {}
        for row in plan_repo.list_all(conn, user_id):
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
