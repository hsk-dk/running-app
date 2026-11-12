from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.db import get_conn
from app.errors import NotConnectedError
from app.repositories import activities as activity_repo
from app.repositories import planned_runs, strava_accounts, user_state
from app.strava import StravaClient

_SYNC_TYPE = "Run"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---- per-user sync state ------------------------------------------------------

def set_state(user_id: int, key: str, value: str) -> None:
    conn = get_conn()
    try:
        user_state.upsert(conn, user_id, key, value)
        conn.commit()
    finally:
        conn.close()


def get_state(user_id: int, key: str):
    conn = get_conn()
    try:
        return user_state.get(conn, user_id, key)
    finally:
        conn.close()


def clear_last_error(user_id: int) -> None:
    set_state(user_id, "last_error", "")


def get_last_synced_start_date(user_id: int):
    state = get_state(user_id, "last_synced_start_date")
    return state["value"] if state else None


def set_last_synced_start_date(user_id: int, value: str):
    set_state(user_id, "last_synced_start_date", value)


def upsert_activity(user_id: int, activity: dict):
    conn = get_conn()
    try:
        activity_repo.upsert(conn, user_id, activity)
        conn.commit()
    finally:
        conn.close()


# ---- Strava access for one user ---------------------------------------------------

def client_for(user_id: int) -> StravaClient:
    """A Strava client for the user's own account. New tokens from Strava are saved as they arrive."""
    conn = get_conn()
    try:
        account = strava_accounts.get(conn, user_id)
    finally:
        conn.close()
    if account is None:
        raise NotConnectedError("Strava er ikke forbundet for denne bruger")

    def save_tokens(refresh_token: str, access_token: str, expires_at: int) -> None:
        c = get_conn()
        try:
            strava_accounts.update_tokens(c, user_id, refresh_token, access_token, expires_at)
            c.commit()
        finally:
            c.close()

    return StravaClient(
        account["refresh_token"], account["access_token"], account["access_expires_at"], on_tokens=save_tokens
    )


# ---- ingest ----------------------------------------------------------------------------

def ingest_recent(user_id: int, pages: int = 3):
    client = client_for(user_id)
    last_synced = get_last_synced_start_date(user_id)
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
            if activity.get("sport_type") != _SYNC_TYPE:
                continue

            upsert_activity(user_id, activity)
            upserted += 1

            start_date = activity.get("start_date")
            if start_date:
                dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if newest_seen is None or dt > newest_seen:
                    newest_seen = dt

    if newest_seen is not None:
        set_last_synced_start_date(user_id, newest_seen.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))

    result = {"upserted": upserted}
    set_state(user_id, "last_sync_at", _now_iso())
    set_state(user_id, "last_ingest_result", json.dumps(result, ensure_ascii=False))
    clear_last_error(user_id)
    return result


def ingest_latest_window(user_id: int, hours_back: int = 72):
    client = client_for(user_id)
    after_epoch = int((datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp())

    upserted = 0
    for activity in client.get_activities(page=1, per_page=100, after_epoch=after_epoch):
        if activity.get("sport_type") != _SYNC_TYPE:
            continue
        upsert_activity(user_id, activity)
        upserted += 1

    result = {"upserted": upserted, "window_hours": hours_back}
    set_state(user_id, "last_sync_at", _now_iso())
    set_state(user_id, "last_ingest_result", json.dumps(result, ensure_ascii=False))
    clear_last_error(user_id)
    return result


def ingest_single_activity(user_id: int, activity_id: int) -> dict:
    """Fetch one activity from Strava and upsert it (used by webhook create/update events)."""
    activity = client_for(user_id).get_activity(activity_id)

    if activity is None:
        return {"upserted": 0, "reason": "not_found"}
    if activity.get("sport_type") != _SYNC_TYPE:
        return {"upserted": 0, "reason": "not_a_run"}

    upsert_activity(user_id, activity)
    set_state(user_id, "last_sync_at", _now_iso())
    clear_last_error(user_id)
    return {"upserted": 1, "activity_id": int(activity_id)}


def delete_activity(user_id: int, activity_id: int) -> dict:
    """Remove a locally stored activity and any plan links pointing at it."""
    conn = get_conn()
    try:
        planned_runs.unmatch_activity(conn, user_id, activity_id)
        deleted = activity_repo.delete(conn, user_id, activity_id)
        conn.commit()
        return {"deleted": deleted}
    finally:
        conn.close()
