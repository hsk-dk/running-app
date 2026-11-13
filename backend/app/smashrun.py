"""Smashrun's API (https://api.smashrun.com/v1/documentation). Network only; no database."""
from __future__ import annotations

import time
from typing import Callable
from urllib.parse import urlencode

import requests

from app.config import settings

AUTHORIZE_URL = "https://secure.smashrun.com/oauth2/authenticate"
TOKEN_URL = "https://secure.smashrun.com/oauth2/token"
BASE_URL = "https://api.smashrun.com/v1"
SCOPE = "read_activity"
PAGE_SIZE = 100

class SmashrunAuthError(RuntimeError):
    """Smashrun no longer accepts the access token (expired or revoked)."""


# Called with (refresh_token, access_token, expires_at) whenever new tokens are issued.
TokenSaver = Callable[[str, str, int], None]


def authorize_url(redirect_uri: str, state: str) -> str:
    return AUTHORIZE_URL + "?" + urlencode(
        {
            "client_id": settings.SMASHRUN_CLIENT_ID,
            "scope": SCOPE,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
    )


def _token_request(data: dict) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={**data, "client_id": settings.SMASHRUN_CLIENT_ID, "client_secret": settings.SMASHRUN_CLIENT_SECRET},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Smashrun token request failed: {response.status_code} {response.text}")
    payload = response.json()
    payload["expires_at"] = int(time.time()) + int(payload.get("expires_in") or 0)
    return payload


def exchange_code(code: str, redirect_uri: str) -> dict:
    return _token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri})


class SmashrunClient:
    """Reads one person's runs. Refreshes the access token when it is about to expire and reports the new tokens."""

    def __init__(self, refresh_token: str, access_token: str | None = None, access_expires_at: int | None = None, on_tokens: TokenSaver | None = None):
        self._refresh_token = refresh_token
        self._access_token = access_token
        self._expires_at = access_expires_at or 0
        self._on_tokens = on_tokens

    def _token(self) -> str:
        if self._access_token and self._expires_at - 60 > time.time():
            return self._access_token
        if not self._refresh_token:
            # A personal token has no refresh token. If we do not know when it runs out (0), use it until Smashrun
            # says no; if we know it has run out, say so.
            if self._access_token and not self._expires_at:
                return self._access_token
            raise SmashrunAuthError("Smashrun-tokenet er udløbet. Indsæt et nyt under Mere → Mig.")
        payload = _token_request({"grant_type": "refresh_token", "refresh_token": self._refresh_token})
        self._access_token = payload["access_token"]
        self._expires_at = payload["expires_at"]
        self._refresh_token = payload.get("refresh_token") or self._refresh_token  # Smashrun keeps the old one
        if self._on_tokens:
            self._on_tokens(self._refresh_token, self._access_token, self._expires_at)
        return self._access_token

    def _get(self, path: str, params: dict | None = None):
        response = requests.get(
            f"{BASE_URL}{path}", params=params, headers={"Authorization": f"Bearer {self._token()}"}, timeout=30
        )
        if response.status_code == 404:
            return None
        if response.status_code in (401, 403):
            raise SmashrunAuthError("Smashrun afviser adgangen (tokenet er udløbet eller tilbagekaldt). Forbind igen under Mere → Mig.")
        if not response.ok:
            raise RuntimeError(f"Smashrun {path} failed: {response.status_code} {response.text[:200]}")
        return response.json()

    def search(self, from_utc: int | None = None, page: int = 0, count: int = PAGE_SIZE) -> list[dict]:
        """Run summaries (with extras such as elevation gain) added or changed since `from_utc` (epoch seconds)."""
        params: dict = {"count": count, "page": page}
        if from_utc is not None:
            params["fromDateUTC"] = int(from_utc)
        return self._get("/my/activities/search/extended", params) or []

    def get_activity(self, activity_id: int) -> dict | None:
        return self._get(f"/my/activities/{int(activity_id)}")

    def userinfo(self) -> dict | None:
        """The signed-in person. A cheap call that proves the token really works for reading."""
        return self._get("/my/userinfo")

    def splits_km(self, activity_id: int):
        return self._get(f"/my/activities/{int(activity_id)}/splits/km")


def token_info(token: str) -> dict:
    """What Smashrun says about a token (scopes, time left). Best effort: {} if it cannot be read, never an error."""
    try:
        response = requests.get(f"{BASE_URL}/auth/{token}", timeout=30)
        if not response.ok:
            return {}
        info = response.json()
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def expiry_epoch(info: dict, now: float | None = None) -> int | None:
    """When a token runs out (epoch seconds) from whatever Smashrun told us, or None if it did not say.

    Understands seconds left (`expires_in`) and an absolute time given as epoch seconds or an ISO date."""
    now = time.time() if now is None else now
    for key in ("expires_in", "expiresIn", "expires", "expiry", "expires_at", "expiresAt"):
        value = info.get(key)
        if value in (None, "", 0, "0"):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            try:
                from datetime import datetime, timezone

                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return int((dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp())
            except ValueError:
                continue
        if number <= 0:
            continue
        return int(number) if number > 1e9 else int(now + number)  # a big number is already a point in time
    return None
