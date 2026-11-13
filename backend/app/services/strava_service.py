"""Connecting a Strava account to a user. The OAuth state is signed so the callback cannot be forged."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time

from app import strava
from app.config import settings
from app.db import DEFAULT_USER_ID, get_conn
from app.errors import ConflictError, ForbiddenError
from app.repositories import strava_accounts

logger = logging.getLogger(__name__)

STATE_TTL_SECONDS = 15 * 60
_FALLBACK_KEY = secrets.token_hex(32)  # only used when APP_SECRET_KEY is not set


def _key() -> bytes:
    return (settings.APP_SECRET_KEY or _FALLBACK_KEY).encode()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_state(user_id: int, now: float | None = None) -> str:
    payload = _b64(json.dumps({"u": user_id, "e": int((now or time.time()) + STATE_TTL_SECONDS), "n": secrets.token_hex(8)}).encode())
    signature = _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def read_state(state: str, now: float | None = None) -> int:
    """Returns the user id the state was made for, or raises ForbiddenError."""
    try:
        payload, signature = state.split(".", 1)
        expected = _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        data = json.loads(_unb64(payload))
        if data["e"] < (now or time.time()):
            raise ValueError("expired")
        return int(data["u"])
    except Exception as exc:
        raise ForbiddenError("The Strava connection link is invalid or has expired") from exc


def redirect_uri() -> str:
    return settings.STRAVA_REDIRECT_URI or settings.APP_BASE_URL.rstrip("/") + "/api/strava/callback"


def begin_connect(user_id: int) -> dict:
    if not settings.STRAVA_CLIENT_ID:
        raise ConflictError("Strava is not configured (STRAVA_CLIENT_ID is empty)")
    return {"url": strava.authorize_url(redirect_uri(), make_state(user_id))}


def complete_connect(state: str, code: str) -> int:
    """Called from the browser redirect. Saves the athlete's tokens for the user in the state."""
    user_id = read_state(state)
    payload = strava.exchange_code(code)
    athlete_id = str((payload.get("athlete") or {}).get("id") or "")
    if not athlete_id:
        raise ConflictError("Strava did not say who connected")

    conn = get_conn()
    try:
        existing = strava_accounts.get_by_athlete(conn, athlete_id)
        if existing is not None and existing["user_id"] != user_id:
            raise ConflictError("This Strava account is already connected to another user")
        strava_accounts.upsert(
            conn,
            user_id,
            athlete_id,
            payload["refresh_token"],
            payload.get("access_token"),
            int(payload.get("expires_at", 0)),
            payload.get("scope") or strava.SCOPE,
        )
        conn.commit()
    finally:
        conn.close()
    return user_id


def status(user_id: int) -> dict:
    conn = get_conn()
    try:
        row = strava_accounts.get(conn, user_id)
        return {
            "connected": row is not None,
            "athlete_id": row["athlete_id"] if row else None,
            "configured": bool(settings.STRAVA_CLIENT_ID),
        }
    finally:
        conn.close()


def disconnect(user_id: int) -> dict:
    conn = get_conn()
    try:
        strava_accounts.delete(conn, user_id)
        conn.commit()
        return {"connected": False}
    finally:
        conn.close()


def ensure_legacy_account() -> bool:
    """The single-user setup kept its Strava token in the environment. Move it to the first user once."""
    if not (settings.STRAVA_REFRESH_TOKEN and settings.STRAVA_ATHLETE_ID):
        return False
    conn = get_conn()
    try:
        if strava_accounts.get(conn, DEFAULT_USER_ID) or strava_accounts.get_by_athlete(conn, settings.STRAVA_ATHLETE_ID):
            return False
        strava_accounts.upsert(conn, DEFAULT_USER_ID, settings.STRAVA_ATHLETE_ID, settings.STRAVA_REFRESH_TOKEN)
        conn.commit()
        logger.info("Moved the Strava token from the environment to the first user's account")
        return True
    finally:
        conn.close()


def after_connect(user_id: int) -> None:
    """First sync after a user connects Strava. Runs in the background and records failures."""
    from app.services import planning_service, sync_service  # imported late: planning_service is heavier

    try:
        sync_service.ingest_recent(user_id, pages=3)
        planning_service.evaluate_and_sync(user_id)
    except Exception as exc:
        logger.exception("First sync for user %s failed", user_id)
        sync_service.set_state(user_id, "last_error", str(exc))
