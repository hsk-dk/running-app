from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.db import get_conn
from app.repositories import activities as activity_repo
from app.repositories import planned_runs, sync_state
from app.strava import StravaClient


def set_state(key: str, value: str) -> None:
    conn = get_conn()
    try:
        sync_state.upsert(conn, key, value)
        conn.commit()
    finally:
        conn.close()


def get_state(key: str):
    conn = get_conn()
    try:
        return sync_state.get(conn, key)
    finally:
        conn.close()


def clear_last_error() -> None:
    set_state("last_error", "")


def get_last_synced_start_date():
    state = get_state("last_synced_start_date")
    return state["value"] if state else None


def set_last_synced_start_date(value: str):
    set_state("last_synced_start_date", value)


def upsert_activity(activity: dict):
    conn = get_conn()
    try:
        activity_repo.upsert(conn, activity)
        conn.commit()
    finally:
        conn.close()


def ingest_recent(pages: int = 3):
    client = StravaClient()
    last_synced = get_last_synced_start_date()
    after_epoch = None

    if last_synced:
        dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00")) - timedelta(days=2)
        after_epoch = int(dt.replace(tzinfo=timezone.utc).timestamp())

    newest_seen = None
    upserted = 0

    for page in range(1, pages + 1):
        activities = client.get_activities(page=page, per_page=50, after_epoch=after_epoch)
        if not activities:
            break

        for activity in activities:
            if activity.get("sport_type") != "Run":
                continue

            upsert_activity(activity)
            upserted += 1

            start_date = activity.get("start_date")
            if start_date:
                dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if newest_seen is None or dt > newest_seen:
                    newest_seen = dt

    if newest_seen is not None:
        set_last_synced_start_date(
            newest_seen.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )

    result = {"upserted": upserted}
    set_state("last_sync_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    set_state("last_ingest_result", json.dumps(result, ensure_ascii=False))
    clear_last_error()
    return result


def ingest_latest_window(hours_back: int = 72):
    client = StravaClient()
    after_dt = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    after_epoch = int(after_dt.timestamp())

    upserted = 0
    activities = client.get_activities(page=1, per_page=100, after_epoch=after_epoch)

    for activity in activities:
        if activity.get("sport_type") != "Run":
            continue
        upsert_activity(activity)
        upserted += 1

    result = {"upserted": upserted, "window_hours": hours_back}
    set_state("last_sync_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    set_state("last_ingest_result", json.dumps(result, ensure_ascii=False))
    clear_last_error()
    return result


def ingest_single_activity(activity_id: int) -> dict:
    """Fetch one activity from Strava and upsert it (used by webhook create/update events)."""
    client = StravaClient()
    activity = client.get_activity(activity_id)

    if activity is None:
        return {"upserted": 0, "reason": "not_found"}
    if activity.get("sport_type") != "Run":
        return {"upserted": 0, "reason": "not_a_run"}

    upsert_activity(activity)
    set_state("last_sync_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    clear_last_error()
    return {"upserted": 1, "activity_id": int(activity_id)}


def delete_activity(activity_id: int) -> dict:
    """Remove a locally stored activity and any plan links pointing at it."""
    conn = get_conn()
    try:
        planned_runs.unmatch_activity(conn, activity_id)
        deleted = activity_repo.delete(conn, activity_id)
        conn.commit()
        return {"deleted": deleted}
    finally:
        conn.close()
