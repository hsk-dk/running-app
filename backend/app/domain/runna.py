"""Runna's iCalendar feed. Pure: text in, plain dicts out (no database, no network).

The feed has three kinds of entries, told apart by the start of the UID:
  UPCOMING_PLAN_WORKOUT    a workout that is still to come (all-day entry; the planned run)
  COMPLETED_PLAN_WORKOUT   a plan workout that was done (start time = when the run started, local time)
  COMPLETED_NON_PLAN_WORKOUT  a run that was not in the plan
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

UPCOMING = "UPCOMING_PLAN_WORKOUT"
COMPLETED_PLAN = "COMPLETED_PLAN_WORKOUT"
COMPLETED_OTHER = "COMPLETED_NON_PLAN_WORKOUT"

_LINK_LINE = re.compile(r"^\W*View in the Runna app.*$", re.IGNORECASE | re.MULTILINE)


def _unfold(text: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n"))


def _unescape(value: str) -> str:
    """iCalendar text escapes in one pass, so an escaped backslash followed by n is not turned into a newline."""
    return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) in "nN" else m.group(1), value, flags=re.S)


def parse_events(text: str) -> list[dict]:
    """Every VEVENT as {PROPERTY: value}; parameters (`;VALUE=DATE`) are dropped, text is unescaped."""
    events = []
    for block in re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", _unfold(text), re.S):
        props: dict[str, str] = {}
        for line in block.split("\n"):
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            props[name.split(";", 1)[0].strip().upper()] = _unescape(value.strip())
        if props.get("UID"):
            events.append(props)
    return events


def _kind(uid: str) -> str:
    return uid.split("-", 1)[0]


def _parse_when(value: str | None, tz_name: str | None) -> tuple[date, datetime | None] | None:
    """(date, local wall-clock datetime or None for an all-day entry)."""
    if not value:
        return None
    try:
        if "T" not in value:
            return datetime.strptime(value[:8], "%Y%m%d").date(), None
        dt = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
        if value.endswith("Z"):  # UTC: convert to the person's own time zone
            try:
                dt = dt.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(tz_name or "Europe/Copenhagen")).replace(tzinfo=None)
            except Exception:
                pass
        return dt.date(), dt
    except ValueError:
        return None


def clean_title(title: str) -> str:
    """'🏃 5km Easy Run' -> '5km Easy Run'."""
    return re.sub(r"^[^\w]+", "", title or "").strip()


def session_type(title: str) -> str:
    """easy / long / tempo / intervals / recovery / race from Runna's workout name. Unknown names are 'easy'."""
    t = title.lower()
    if "race" in t:
        return "race"
    if "long" in t:
        return "long"
    if "tempo" in t or "threshold" in t:
        return "tempo"
    if re.search(r"repeat|interval|fartlek|stride|hill|\b\d+m\b|\b\d+s\b|\bx\s?\d", t):
        return "intervals"
    if "recovery" in t:
        return "recovery"
    return "easy"


def _distance_km(title: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*km", title.lower())
    return float(m.group(1).replace(",", ".")) if m else None


def _notes(description: str) -> str | None:
    text = _LINK_LINE.sub("", description or "").strip()
    return text[:600] or None


def planned_runs(events: list[dict]) -> list[dict]:
    """The upcoming plan workouts, ready to be stored as planned runs."""
    out = []
    for e in events:
        uid = e["UID"]
        if _kind(uid) != UPCOMING:
            continue
        when = _parse_when(e.get("DTSTART"), e.get("X-USER-TIMEZONE"))
        if when is None:
            continue
        title = clean_title(e.get("SUMMARY", ""))
        km = _distance_km(title)
        seconds = None
        try:
            seconds = float(e["X-WORKOUT-ESTIMATED-DURATION"]) if e.get("X-WORKOUT-ESTIMATED-DURATION") else None
        except ValueError:
            seconds = None
        if km:
            target_type, target_value = "distance", km
        elif seconds and seconds > 0:
            target_type, target_value = "time", float(round(seconds / 60))
        else:
            target_type, target_value = "time", None
        out.append(
            {
                "external_uid": uid,
                "planned_date": when[0].isoformat(),
                "session_type": session_type(title),
                "target_type": target_type,
                "target_value": target_value,
                "title": title,
                "notes": _notes(e.get("DESCRIPTION", "")) or title,
            }
        )
    return out


_SUMMARY_DISTANCE = re.compile(r"Distance:\s*(\d+(?:[.,]\d+)?)\s*km", re.IGNORECASE)
_PLANNED_TEXT = re.compile(r"Description:\s*\n(.*?)(?:\n\W*Laps:|\n\W*View in the Runna app|\Z)", re.IGNORECASE | re.DOTALL)


def completed_plan_runs(events: list[dict]) -> list[dict]:
    """Plan workouts that were done, as planned runs: what Runna had planned for a day that is now in the past.

    The target is the distance in the workout's name ("5km Easy Run"); a workout named only by its kind ("Taper 400s")
    has no planned distance in the feed, so what was run stands in for it. Runna does not list workouts that were skipped,
    so history shows done sessions only."""
    out = []
    for e in events:
        uid = e["UID"]
        if _kind(uid) != COMPLETED_PLAN:
            continue
        when = _parse_when(e.get("DTSTART"), e.get("X-USER-TIMEZONE"))
        title = clean_title(e.get("SUMMARY", ""))
        if when is None or not title:
            continue
        description = e.get("DESCRIPTION", "")
        km = _distance_km(title)
        if km is None:
            actual = _SUMMARY_DISTANCE.search(description)
            km = float(actual.group(1).replace(",", ".")) if actual else None
        if not km:
            continue
        planned = _PLANNED_TEXT.search(description)
        text = (planned.group(1).strip() if planned else "")[:600]
        garmin = re.search(r"-garmin-(\d+)$", uid)
        out.append(
            {
                "external_uid": uid,
                "planned_date": when[0].isoformat(),
                "session_type": session_type(title),
                "target_type": "distance",
                "target_value": km,
                "title": title,
                "notes": text or title,
                "garmin_id": int(garmin.group(1)) if garmin else None,
            }
        )
    return out


def completed_runs(events: list[dict]) -> list[dict]:
    """Done runs with Runna's name for them and the local start time (used to name the matching activity)."""
    out = []
    for e in events:
        if _kind(e["UID"]) not in (COMPLETED_PLAN, COMPLETED_OTHER):
            continue
        when = _parse_when(e.get("DTSTART"), e.get("X-USER-TIMEZONE"))
        title = clean_title(e.get("SUMMARY", ""))
        if when is None or when[1] is None or not title:
            continue
        out.append({"uid": e["UID"], "start_local": when[1].strftime("%Y-%m-%dT%H:%M:%SZ"), "name": title})
    return out
