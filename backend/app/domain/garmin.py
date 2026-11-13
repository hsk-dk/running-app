"""Garmin Connect activities in the shape the rest of the app knows. Pure.

Garmin's own ids are stored negated and shifted far out, so they can never meet Strava's positive ids or Smashrun's
small negative ones.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

SOURCE = "garmin"
ID_BASE = 10**12

# Garmin's activity types that are runs. Indoor/treadmill ones have no GPS.
TREADMILL_TYPES = {"treadmill_running", "indoor_running", "virtual_run"}
RUN_TYPES = TREADMILL_TYPES | {"running", "trail_running", "track_running", "street_running", "ultra_run", "obstacle_run"}


def internal_id(garmin_id: int | str) -> int:
    return -(ID_BASE + abs(int(garmin_id)))


def garmin_id_of(internal: int) -> int | None:
    return abs(int(internal)) - ID_BASE if internal <= -ID_BASE else None


def _first(summary: dict, *keys: str) -> Any:
    for key in keys:
        if summary.get(key) is not None:
            return summary[key]
    return None


def _num(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def type_key(summary: dict) -> str | None:
    kind = summary.get("activityType")
    if isinstance(kind, dict):
        kind = kind.get("typeKey")
    kind = kind or summary.get("type")
    return str(kind).lower() if kind else None


def is_treadmill(summary_or_key: dict | str | None) -> bool:
    key = type_key(summary_or_key) if isinstance(summary_or_key, dict) else summary_or_key
    return (key or "") in TREADMILL_TYPES


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "").replace("T", " ")[:19])
    except ValueError:
        return None


def activity_from_summary(summary: dict, tz_name: str = "Europe/Copenhagen") -> dict | None:
    """One Garmin activity as an app activity, or None if it is not a run with a start, a distance and a time."""
    if not isinstance(summary, dict):
        return None
    key = type_key(summary)
    if key not in RUN_TYPES:
        return None
    gid = _first(summary, "activityId", "id")
    local = _parse(_first(summary, "startTimeLocal", "start_time_local", "start_time"))
    gmt = _parse(_first(summary, "startTimeGMT", "start_time_gmt"))
    distance = _num(_first(summary, "distance", "distance_meters"))
    duration = _num(_first(summary, "duration", "duration_seconds"))
    if gid is None or local is None or not distance or distance <= 0 or not duration or duration <= 0:
        return None
    if gmt is None:  # no UTC time given: work it out from the wall-clock time and the person's time zone
        try:
            gmt = local.replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            gmt = local
    try:
        internal = internal_id(gid)
    except (TypeError, ValueError):
        return None
    moving = _num(_first(summary, "movingDuration", "moving_duration_seconds")) or duration
    cadence = _num(_first(summary, "averageRunningCadenceInStepsPerMinute", "averageCadence"))
    return {
        "id": internal,
        "garmin_id": int(gid),
        "name": (str(_first(summary, "activityName", "name")).strip() or None) if _first(summary, "activityName", "name") else None,
        "sport_type": "Run",
        "start_date": gmt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start_date_local": local.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "distance": distance,
        "moving_time": int(round(moving)),
        "elapsed_time": int(round(duration)),
        "total_elevation_gain": _num(_first(summary, "elevationGain", "elevation_gain_meters")),
        "average_speed": distance / moving if moving else None,
        "average_heartrate": _num(_first(summary, "averageHR", "avg_hr_bpm")),
        "max_heartrate": _num(_first(summary, "maxHR", "max_hr_bpm")),
        "average_cadence": cadence,
        "garmin_type": key,
        "treadmill": key in TREADMILL_TYPES,
    }
