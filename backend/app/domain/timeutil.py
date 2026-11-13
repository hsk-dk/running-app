"""All calendar logic uses the user's local time zone (APP_TIMEZONE).

Planned dates are local calendar dates. An activity's date is the source's
`start_date_local` (where the run happened); if that is missing, the UTC
`start_date` is converted to APP_TIMEZONE.

Callers must use `timeutil.today()` / `timeutil.local_now()` (attribute access)
so tests can patch them.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings


def app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.APP_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def local_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(app_timezone())


def today() -> date:
    return local_now().date()


def parse_planned_date(value: str) -> date:
    """Accepts 'YYYY-MM-DD' or an ISO datetime; only the calendar date matters."""
    return date.fromisoformat(str(value).strip()[:10])


def activity_local_date(row) -> date | None:
    """Local calendar date of an activity row/dict, or None if it has no usable start."""
    local = _get(row, "start_date_local")
    if local:
        try:
            return date.fromisoformat(str(local)[:10])
        except ValueError:
            pass

    start = _get(row, "start_date")
    if not start:
        return None
    try:
        dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(app_timezone()).date()


def _get(row, key):
    try:
        return row[key]
    except (KeyError, IndexError):
        return None
