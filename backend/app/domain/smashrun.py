"""Smashrun runs in the shape the rest of the app already knows (Strava-like dicts). Pure: no database, no network.

Smashrun's own ids are stored negated so they can never collide with Strava's positive ids.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SOURCE = "smashrun"


def internal_id(smashrun_id: int | str) -> int:
    return -abs(int(smashrun_id))


def smashrun_id(internal: int) -> int:
    return abs(int(internal))


def _parse_start(value: Any) -> tuple[str, str] | None:
    """(UTC start 'YYYY-MM-DDTHH:MM:SSZ', local wall-clock 'YYYY-MM-DDTHH:MM:SSZ') from an ISO 8601 string, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    local = dt.replace(microsecond=0, tzinfo=None)
    utc = (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ"), local.strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def activity_from_summary(summary: dict) -> dict | None:
    """One Smashrun activity (summary or detail) as an app activity, or None if it is not a usable run."""
    if not isinstance(summary, dict):
        return None
    raw_id = summary.get("activityId", summary.get("id"))
    start = _parse_start(summary.get("startDateTimeLocal"))
    distance_km = _num(summary.get("distance"))
    duration_s = _num(summary.get("duration"))
    if raw_id is None or start is None or not distance_km or distance_km <= 0 or not duration_s or duration_s <= 0:
        return None
    try:
        internal = internal_id(raw_id)
    except (TypeError, ValueError):
        return None

    notes = (summary.get("notes") or "").strip()
    name = notes.splitlines()[0][:80] if notes else None
    return {
        "id": internal,
        "name": name,
        "sport_type": "Run",
        "start_date": start[0],
        "start_date_local": start[1],
        "distance": distance_km * 1000.0,
        "moving_time": int(round(duration_s)),
        "elapsed_time": int(round(duration_s)),
        "total_elevation_gain": _num(summary.get("elevationGain")),
        "average_speed": (distance_km * 1000.0) / duration_s,
        "average_heartrate": _num(summary.get("heartRateAverage")),
        "max_heartrate": _num(summary.get("heartRateMax")),
        "average_cadence": _num(summary.get("cadenceAverage")),
        "terrain": summary.get("terrain"),
        "source": SOURCE,
        "smashrun": summary,
    }
