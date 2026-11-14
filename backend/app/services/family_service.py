"""What family members may see of each other. Everything is private until a person shares it themselves."""
from __future__ import annotations

from app.config import settings
from app.db import get_conn
from datetime import timedelta

from app.domain import firsts as firsts_domain
from app.domain import timeutil, weekly
from app.domain.runs import is_mandatory
from app.domain.statuses import STATUS_FLYTTET
from app.errors import ForbiddenError
from app.repositories import activities as activity_repo
from app.repositories import planned_runs as plan_repo
from app.repositories import sync_state
from app.services import challenge_service, firsts_service, garmin_service, reporting_service, splits_service, user_service
from app.services.user_service import CurrentUser

RECENT_RUNS = 8


def access_level(viewer: CurrentUser, target: CurrentUser) -> str:
    """What the viewer may see of the target:

    - 'all' for yourself
    - 'guardian' for a parent looking at a child: a short summary, whatever the child has chosen
    - 'private' when the person shares nothing (or sharing is off)
    - 'milestones' when a child is involved on either side: only the milestones, never kilometres or runs
    - otherwise what the person has chosen to share ('overview' or 'all')
    """
    if viewer.id == target.id:
        return "all"
    if target.is_child and viewer.is_admin:
        return "guardian"
    sharing = target.sharing_level if settings.FAMILY_SHARING_ENABLED else "private"
    if sharing == "private":
        return "private"
    if target.is_child or viewer.is_child:
        return "milestones"
    return sharing


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


def _guardian_view(conn, user_id: int, today) -> dict:
    """What a parent sees about a child: how often and how long, not how far or how fast, and no places."""
    runs = []
    for row in activity_repo.list_runs_for_metrics(conn, user_id):
        day = timeutil.activity_local_date(row)
        if day is not None and float(row["distance_m"] or 0) / 1000.0 >= firsts_domain.MIN_RUN_KM:
            runs.append((day, float(row["moving_time_s"] or 0) / 60.0))
    monday = today - timedelta(days=today.weekday())
    week = [(d, m) for d, m in runs if monday <= d <= today]
    month = [(d, m) for d, m in runs if (d.year, d.month) == (today.year, today.month) and d <= today]
    return {
        "runs_week": len(week),
        "active_days_week": len({d for d, _ in week}),
        "minutes_week": round(sum(m for _, m in week)),
        "runs_month": len(month),
        "minutes_month": round(sum(m for _, m in month)),
        "last_run_date": max((d for d, _ in runs), default=None).isoformat() if runs else None,
        "streak_weeks": weekly.streak([d for d, _ in runs], today),
    }


def _member(viewer: CurrentUser, target: CurrentUser) -> dict:
    level = access_level(viewer, target)
    conn = get_conn()
    try:
        entry = {
            "user_id": target.id,
            "name": target.display_name,
            "is_me": viewer.id == target.id,
            "level": level,
            "shared": level != "private" or viewer.id == target.id,
            "week": None,
            "month_km": None,
            "month_runs": None,
            "streak_weeks": None,
            "recent_runs": None,
            "new_milestones": None,
            "is_child": target.is_child,
            "guardian": None,
        }
        if not entry["shared"]:
            return entry

        today = timeutil.today()
        if level == "guardian":
            entry["guardian"] = _guardian_view(conn, target.id, today)
            extra = challenge_service.for_family(target.id)
            entry["guardian"]["challenges"] = extra["items"]
            entry["new_milestones"] = firsts_service.recent_for_family(target.id) + extra["milestones"]
            return entry
        if level == "milestones":
            entry["new_milestones"] = firsts_service.recent_for_family(target.id) + challenge_service.for_family(target.id)["milestones"]
            return entry
        entry["week"] = _week_numbers(conn, target.id, today)
        entry["streak_weeks"] = _streak(conn, target.id, today)
        entry["new_milestones"] = firsts_service.recent_for_family(target.id) + challenge_service.for_family(target.id)["milestones"]
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


GOAL_KEY = "family_goal_km"


def _goal(users) -> dict:
    """The family's monthly goal and how far everyone who shares has come together. One number: nobody's part is shown."""
    today = timeutil.today()
    conn = get_conn()
    try:
        raw = sync_state.get(conn, GOAL_KEY)
    finally:
        conn.close()
    try:
        target = float(raw) if raw else None
    except ValueError:
        target = None
    km = 0.0
    for u in users:
        if u.sharing_level != "private":  # sharing_level is already 'private' when family sharing is off
            km += reporting_service.summary(u.id)["km_this_month"] or 0
    return {"target_km": target, "km": round(km, 1), "month": today.strftime("%Y-%m")}


def set_goal(admin: CurrentUser, target_km: float | None) -> dict:
    if not admin.is_admin:
        raise ForbiddenError("Only an admin can set the family's goal")
    conn = get_conn()
    try:
        if target_km is None:
            sync_state.delete(conn, GOAL_KEY)
        else:
            sync_state.upsert(conn, GOAL_KEY, str(target_km))
        conn.commit()
    finally:
        conn.close()
    return _goal(user_service.list_users())


def list_family(viewer: CurrentUser) -> dict:
    users = user_service.list_users()
    members = [_member(viewer, u) for u in users]
    members.sort(key=lambda m: (not m["is_me"], m["name"].lower()))
    goal = _goal(users)
    names = {u.id: u.display_name for u in users}
    brags = [{**b, "name": names.get(b["user_id"], "?"), "is_me": b["user_id"] == viewer.id} for b in challenge_service.recent_brags() if b["user_id"] in names]
    return {
        "members": members,
        "total_km_this_month": goal["km"],
        "sharing_enabled": settings.FAMILY_SHARING_ENABLED,
        "goal": goal,
        "brags": brags,
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


def member_splits(viewer: CurrentUser, user_id: int, activity_id: int):
    target = _target(viewer, user_id)
    result = splits_service.get_splits(target.id, activity_id)
    # Heart rate is never shared with the family, not even per kilometre.
    return {**result, "splits": [{**split, "avg_hr": None} for split in result["splits"]]}


def member_profile(viewer: CurrentUser, user_id: int, activity_id: int):
    target = _target(viewer, user_id)
    return garmin_service.get_profile(target.id, activity_id, include_hr=False)
