from __future__ import annotations

import json

from app.config import settings
from app.db import get_conn
from app.ingest import ingest_latest_window
from app.metrics import rebuild_metrics
from app.planning import evaluate_and_sync


def verify_subscription(mode: str, token: str, challenge: str):
    if mode != "subscribe":
        return None
    if token != settings.STRAVA_VERIFY_TOKEN:
        return None
    return {"hub.challenge": challenge}


def store_event(payload: dict):
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO webhook_events (
                provider, object_type, object_id, aspect_type,
                owner_id, subscription_id, event_time, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "strava",
                payload.get("object_type"),
                str(payload.get("object_id")) if payload.get("object_id") is not None else None,
                payload.get("aspect_type"),
                str(payload.get("owner_id")) if payload.get("owner_id") is not None else None,
                str(payload.get("subscription_id")) if payload.get("subscription_id") is not None else None,
                payload.get("event_time"),
                json.dumps(payload),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def mark_event_processed(event_id: int):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE webhook_events
            SET processed = 1, processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (event_id,),
        )
        conn.commit()
    finally:
        conn.close()


def process_event(payload: dict):
    event_id = store_event(payload)

    owner_id = str(payload.get("owner_id", ""))
    object_type = payload.get("object_type")

    if settings.STRAVA_ATHLETE_ID and owner_id and owner_id != settings.STRAVA_ATHLETE_ID:
        mark_event_processed(event_id)
        return {
            "stored": True,
            "processed": True,
            "ignored": True,
            "reason": "owner_mismatch",
        }

    if object_type == "activity":
        ingest_result = ingest_latest_window(hours_back=72)
        metrics_result = rebuild_metrics()
        planning_result = evaluate_and_sync()

        mark_event_processed(event_id)
        return {
            "stored": True,
            "processed": True,
            "ingest": ingest_result,
            "metrics": metrics_result,
            "planning": planning_result,
        }

    mark_event_processed(event_id)
    return {
        "stored": True,
        "processed": True,
        "ignored": True,
        "reason": "unsupported_object_type",
    }
