from __future__ import annotations

import json
import logging

from app.admin_status import set_state
from app.config import settings
from app.db import get_conn
from app.ingest import delete_activity, ingest_single_activity
from app.planning import evaluate_and_sync
from app.repositories import webhook_events

logger = logging.getLogger(__name__)


def verify_subscription(mode: str, token: str, challenge: str):
    if mode != "subscribe":
        return None
    if token != settings.STRAVA_VERIFY_TOKEN:
        return None
    return {"hub.challenge": challenge}


def _text(value):
    return str(value) if value is not None else None


def store_event(payload: dict) -> tuple[int, bool, bool]:
    """Store an event. Returns (event_id, is_duplicate, already_processed).

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
            return existing["id"], True, bool(existing["processed"])

        event_id = webhook_events.insert(
            conn,
            key[0], key[1], key[2], key[3],
            _text(payload.get("subscription_id")),
            key[4],
            json.dumps(payload),
        )
        conn.commit()
        return event_id, False, False
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
    event_id, duplicate, processed = store_event(payload)
    set_state("last_webhook_at", _now_iso())

    needs_processing = not processed
    return {
        "stored": True,
        "duplicate": duplicate,
        "event_id": event_id,
        "needs_processing": needs_processing,
    }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def process_stored_event(event_id: int, payload: dict) -> dict:
    """Slow path, run in the background. Never raises; failures are recorded."""
    try:
        owner_id = str(payload.get("owner_id", ""))
        object_type = payload.get("object_type")
        aspect_type = payload.get("aspect_type")

        if settings.STRAVA_ATHLETE_ID and owner_id and owner_id != settings.STRAVA_ATHLETE_ID:
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "owner_mismatch"}

        if object_type != "activity":
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "unsupported_object_type"}

        object_id = payload.get("object_id")
        if object_id is None:
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "missing_object_id"}
        activity_id = int(object_id)

        if aspect_type == "delete":
            activity_result = delete_activity(activity_id)
        elif aspect_type in ("create", "update"):
            activity_result = ingest_single_activity(activity_id)
        else:
            mark_event_processed(event_id)
            return {"ignored": True, "reason": "unsupported_aspect_type"}

        planning_result = evaluate_and_sync()
        mark_event_processed(event_id)
        set_state("last_error", "")
        return {"activity": activity_result, "planning": planning_result}
    except Exception as exc:
        # Left unprocessed so a Strava retry (or manual replay) can pick it up again.
        logger.exception("Webhook event %s failed", event_id)
        set_state("last_error", f"webhook event {event_id}: {exc}")
        return {"error": str(exc)}
