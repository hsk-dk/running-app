from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.config import settings
from app.db import get_conn
from app.repositories import strava_accounts, sync_state, user_state, webhook_events
from app.services.planning_service import evaluate_and_sync
from app.services.sync_service import delete_activity, ingest_single_activity, set_state

logger = logging.getLogger(__name__)


def verify_subscription(mode: str, token: str, challenge: str):
    if mode != "subscribe":
        return None
    if token != settings.STRAVA_VERIFY_TOKEN:
        return None
    return {"hub.challenge": challenge}


def _text(value):
    return str(value) if value is not None else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _user_for_owner(conn, owner_id: str | None) -> int | None:
    """The user whose Strava account has this athlete id (Strava calls it owner_id), if any."""
    if not owner_id:
        return None
    account = strava_accounts.get_by_athlete(conn, owner_id)
    return account["user_id"] if account else None


def store_event(payload: dict) -> tuple[int, bool, bool, int | None]:
    """Store an event. Returns (event_id, is_duplicate, already_processed, user_id).

    Strava retries deliveries, so an identical event (same object, aspect,
    owner and event_time) is not stored twice.
    """
    key = (
        _text(payload.get("object_type")),
        _text(payload.get("object_id")),
        _text(payload.get("aspect_type")),
        _text(payload.get("owner_id")),
        payload.get("event_time"),
    )
    conn = get_conn()
    try:
        existing = webhook_events.find_duplicate(conn, key)
        if existing:
            user_id = _user_for_owner(conn, key[3])
            return existing["id"], True, bool(existing["processed"]), user_id

        user_id = _user_for_owner(conn, key[3])
        event_id = webhook_events.insert(
            conn,
            key[0], key[1], key[2], key[3],
            _text(payload.get("subscription_id")),
            key[4],
            json.dumps(payload),
            user_id,
        )
        conn.commit()
        return event_id, False, False, user_id
    finally:
        conn.close()


def mark_event_processed(event_id: int):
    conn = get_conn()
    try:
        webhook_events.mark_processed(conn, event_id)
        conn.commit()
    finally:
        conn.close()


def receive_event(payload: dict) -> dict:
    """Fast path: persist the event and decide whether it needs processing.

    Must stay cheap, since Strava expects a reply within ~2 seconds.
    """
    event_id, duplicate, processed, user_id = store_event(payload)

    conn = get_conn()
    try:
        now = _now_iso()
        sync_state.upsert(conn, "last_webhook_at", now)
        if user_id is not None:
            user_state.upsert(conn, user_id, "last_webhook_at", now)
        conn.commit()
    finally:
        conn.close()

    return {
        "stored": True,
        "duplicate": duplicate,
        "event_id": event_id,
        "needs_processing": not processed,
    }


def process_stored_event(event_id: int, payload: dict) -> dict:
    """Slow path, run in the background. Never raises; failures are recorded."""
    user_id: int | None = None
    try:
        conn = get_conn()
        try:
            user_id = _user_for_owner(conn, _text(payload.get("owner_id")))
        finally:
            conn.close()

        if user_id is None:
            # Nobody here has connected this athlete. Nothing to do, and nothing to retry.
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "unknown_owner"}

        if payload.get("object_type") != "activity":
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "unsupported_object_type"}

        object_id = payload.get("object_id")
        if object_id is None:
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "missing_object_id"}
        activity_id = int(object_id)

        aspect_type = payload.get("aspect_type")
        if aspect_type == "delete":
            activity_result = delete_activity(user_id, activity_id)
        elif aspect_type in ("create", "update"):
            activity_result = ingest_single_activity(user_id, activity_id)
        else:
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "unsupported_aspect_type"}

        planning_result = evaluate_and_sync(user_id)
        mark_event_processed(event_id)
        set_state(user_id, "last_error", "")
        return {"activity": activity_result, "planning": planning_result}
    except Exception as exc:
        # Left unprocessed so a Strava retry (or manual replay) can pick it up again.
        logger.exception("Webhook event %s failed", event_id)
        if user_id is not None:
            set_state(user_id, "last_error", f"webhook event {event_id}: {exc}")
        return {"error": str(exc)}
