"""Connecting a person's Smashrun account and pulling their runs from it."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from app import smashrun
from app.config import settings
from app.db import get_conn
from app.domain import smashrun as domain
from app.errors import ConflictError, ForbiddenError, NotConnectedError
from app.repositories import activities as activity_repo
from app.repositories import smashrun_accounts, user_state
from app.services import strava_service  # the signed connect link is shared with Strava

logger = logging.getLogger(__name__)

OVERLAP_SECONDS = 2 * 24 * 3600  # re-read a little before the last sync: runs can be edited after upload
DUPLICATE_WINDOW_SECONDS = 120


def redirect_uri() -> str:
    return settings.SMASHRUN_REDIRECT_URI or settings.APP_BASE_URL.rstrip("/") + "/api/smashrun/callback"


def configured() -> bool:
    return bool(settings.SMASHRUN_CLIENT_ID and settings.SMASHRUN_CLIENT_SECRET)


def read_state(state: str) -> int:
    try:
        return strava_service.read_state(state)
    except ForbiddenError as exc:
        raise ForbiddenError("The Smashrun connection link is invalid or has expired") from exc


def begin_connect(user_id: int) -> dict:
    if not configured():
        raise ConflictError("Smashrun is not configured (SMASHRUN_CLIENT_ID and SMASHRUN_CLIENT_SECRET)")
    return {"url": smashrun.authorize_url(redirect_uri(), strava_service.make_state(user_id))}


def complete_connect(state: str, code: str) -> int:
    user_id = read_state(state)
    payload = smashrun.exchange_code(code, redirect_uri())
    if not payload.get("access_token"):
        raise ConflictError("Smashrun did not return an access token")
    conn = get_conn()
    try:
        smashrun_accounts.upsert(
            conn, user_id, payload.get("refresh_token") or "", payload["access_token"], int(payload["expires_at"]), smashrun.SCOPE
        )
        conn.commit()
    finally:
        conn.close()
    return user_id


def status(user_id: int) -> dict:
    conn = get_conn()
    try:
        return {"connected": smashrun_accounts.get(conn, user_id) is not None, "configured": configured()}
    finally:
        conn.close()


def disconnect(user_id: int) -> dict:
    conn = get_conn()
    try:
        smashrun_accounts.delete(conn, user_id)
        user_state.upsert(conn, user_id, "smashrun_last_sync_utc", "")
        conn.commit()
    finally:
        conn.close()
    return status(user_id)


def client_for(user_id: int) -> smashrun.SmashrunClient:
    conn = get_conn()
    try:
        account = smashrun_accounts.get(conn, user_id)
    finally:
        conn.close()
    if account is None:
        raise NotConnectedError("Smashrun er ikke forbundet for denne bruger")

    def save_tokens(refresh_token: str, access_token: str, expires_at: int) -> None:
        c = get_conn()
        try:
            smashrun_accounts.update_tokens(c, user_id, refresh_token, access_token, expires_at)
            c.commit()
        finally:
            c.close()

    return smashrun.SmashrunClient(account["refresh_token"], account["access_token"], account["access_expires_at"], on_tokens=save_tokens)


def ingest_recent(user_id: int, full: bool = False) -> dict:
    """Pull new and changed runs. The same run already stored from another source (e.g. Strava) is not added twice."""
    client = client_for(user_id)
    started = int(time.time())

    conn = get_conn()
    try:
        last = user_state.get(conn, user_id, "smashrun_last_sync_utc")
    finally:
        conn.close()
    from_utc = None if full or not last or not last["value"] else max(0, int(last["value"]) - OVERLAP_SECONDS)

    added = updated = duplicates = skipped = 0
    page = 0
    while True:
        batch = client.search(from_utc=from_utc, page=page, count=smashrun.PAGE_SIZE)
        for summary in batch:
            activity = domain.activity_from_summary(summary)
            if activity is None:
                skipped += 1
                continue
            conn = get_conn()
            try:
                existing = activity_repo.get(conn, user_id, activity["id"])
                if existing is None and activity_repo.find_near(conn, user_id, activity["start_date"], DUPLICATE_WINDOW_SECONDS):
                    duplicates += 1
                    continue
                activity_repo.upsert(conn, user_id, activity, source=domain.SOURCE, source_id=str(domain.smashrun_id(activity["id"])))
                conn.commit()
            finally:
                conn.close()
            updated += existing is not None
            added += existing is None
        if len(batch) < smashrun.PAGE_SIZE:
            break
        page += 1

    result = {"source": "smashrun", "added": added, "updated": updated, "duplicates": duplicates, "skipped": skipped}
    conn = get_conn()
    try:
        user_state.upsert(conn, user_id, "smashrun_last_sync_utc", str(started))
        user_state.upsert(conn, user_id, "last_sync_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        user_state.upsert(conn, user_id, "last_ingest_result", json.dumps(result, ensure_ascii=False))
        user_state.upsert(conn, user_id, "last_error", "")
        conn.commit()
    finally:
        conn.close()
    return result


def after_connect(user_id: int) -> None:
    """First sync after connecting: the whole history. Runs in the background and records failures."""
    from app.services import planning_service  # imported late: heavier

    try:
        ingest_recent(user_id, full=True)
        planning_service.evaluate_and_sync(user_id)
    except Exception as exc:  # background task: nobody is waiting for the answer
        logger.exception("First Smashrun sync failed")
        c = get_conn()
        try:
            user_state.upsert(c, user_id, "last_error", str(exc))
            c.commit()
        finally:
            c.close()
