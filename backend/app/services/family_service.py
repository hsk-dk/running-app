"""What family members may see of each other. Everything is private until a person shares it themselves."""
from __future__ import annotations

from app.config import settings
from app.db import get_conn
from app.domain import timeutil, weekly
from app.domain.runs import is_mandatory
from app.domain.statuses import STATUS_FLYTTET
from app.errors import ForbiddenError
from app.repositories import activities as activity_repo
from app.repositories import planned_runs as plan_repo
from app.repositories import strava_accounts
from app.services import reporting_service, user_service
from app.services.user_service import CurrentUser

RECENT_RUNS = 8


def access_level(viewer: CurrentUser, target: CurrentUser) -> str:
    """'all' for yourself, otherwise what the other person has chosen to share (private when sharing is off)."""
    if viewer.id == target.id:
        return "all"
    return target.sharing_level if settings.FAMILY_SHARING_ENABLED else "private"


def _week_numbers(conn, user_id: int, today) -> dict:
    current = weekly.iso_week_key(today)
    plans = []
    for row in plan_repo.list_all(conn, user_id):
        if not is_mandatory(row) or row["status"] == STATUS_FLYTTET:
            continue
        try:
            planned = timeutil.parse_planned_date(row["planned_date"])
        except ValueError:
            continue
        if weekly.iso_week_key(planned) == current:
            plans.append((planned, row["status"]))
    summary = weekly.summarize(plans, today)
    return {"done": summary["completed"] + summary["shortened"], "total": summary["mandatory_runs"], "open": summary["awaiting"]}


def _streak(conn, user_id: int, today) -> int:
    dates = [timeutil.activity_local_date(r) for r in activity_repo.list_runs_for_metrics(conn, user_id)]
    return weekly.streak([d for d in dates if d is not None], today)


def _member(viewer: CurrentUser, target: CurrentUser) -> dict:
    level = access_level(viewer, target)
    conn = get_conn()
    try:
        connected = strava_accounts.get(conn, target.id) is not None
        entry = {
            "user_id": target.id,
            "name": target.display_name,
            "is_me": viewer.id == target.id,
            "level": level,
            "shared": level != "private" or viewer.id == target.id,
            "strava_connected": connected,
            "week": None,
            "month_km": None,
            "month_runs": None,
            "streak_weeks": None,
            "recent_runs": None,
        }
        if not entry["shared"] or not connected:
            return entry

        today = timeutil.today()
        entry["week"] = _week_numbers(conn, target.id, today)
        entry["streak_weeks"] = _streak(conn, target.id, today)
    finally:
        conn.close()

    month = reporting_service.summary(target.id)
    entry["month_km"] = month["km_this_month"]
    entry["month_runs"] = month["runs_this_month"]
    if level == "all":
        runs = reporting_service.list_activities(target.id, limit=RECENT_RUNS)
        entry["recent_runs"] = [
            {k: r[k] for k in ("id", "date", "name", "distance_km", "duration_min")} for r in runs
        ]
    return entry


def list_family(viewer: CurrentUser) -> dict:
    users = user_service.list_users()
    members = [_member(viewer, u) for u in users]
    members.sort(key=lambda m: (not m["is_me"], m["name"].lower()))
    total = sum(m["month_km"] or 0 for m in members)
    return {
        "members": members,
        "total_km_this_month": round(total, 1),
        "sharing_enabled": settings.FAMILY_SHARING_ENABLED,
    }


def _target(viewer: CurrentUser, user_id: int) -> CurrentUser:
    target = user_service.get_user(user_id)  # raises NotFoundError for an unknown user
    if access_level(viewer, target) != "all":
        raise ForbiddenError("This person has not shared their runs")
    return target


def member_activities(viewer: CurrentUser, user_id: int, limit: int = 20):
    target = _target(viewer, user_id)
    return reporting_service.list_activities(target.id, limit=limit)


def member_activity(viewer: CurrentUser, user_id: int, activity_id: int):
    target = _target(viewer, user_id)
    return reporting_service.get_activity(target.id, activity_id)
