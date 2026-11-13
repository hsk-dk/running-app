"""The signed 'state' that travels with a connect link, so the callback knows who is connecting. No account is needed to
check it: it is signed with APP_SECRET_KEY and runs out after a few minutes."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from app.config import settings
from app.errors import ForbiddenError

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
    """The user id the state was made for, or ForbiddenError if it is forged or has expired."""
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
        raise ForbiddenError("Forbindelseslinket er ugyldigt eller udløbet") from exc
