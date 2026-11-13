"""Garmin's Personal API (https://developer.garmin.com/gc-developer-program/personal/). Network only; no database.

The person makes a key in Garmin Connect; we swap it for a short-lived bearer token (a JWT) and read their own
activities with it. Endpoints and headers follow Garmin's own Python client (garmin/connect-personal-api-python).
"""
from __future__ import annotations

import base64
import json
import time
from typing import Callable

import requests

BASE_URL = "https://personal.connectapi.garmin.com"
TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"
REFRESH_WINDOW_SECONDS = 60 * 60  # ask for a new token when less than an hour is left
PAGE_SIZE = 100
MAX_ZIP_BYTES = 30 * 1024 * 1024

# Called with (bearer_token, expires_at) whenever a new token has been issued.
TokenSaver = Callable[[str, int], None]


class GarminAuthError(RuntimeError):
    """Garmin does not accept the key or the token."""


def _jwt_exp(token: str) -> int:
    try:
        payload = token.split(".")[1]
        return int(float(json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["exp"]))
    except Exception as exc:
        raise GarminAuthError("Garmin svarede med et token, der ikke kan læses") from exc


def exchange_key(api_key: str) -> tuple[str, int]:
    """(bearer token, expiry) for a personal API key."""
    response = requests.post(
        f"{BASE_URL}{TOKEN_PATH}", headers={"Accept": "*/*", "Authorization": f"ApiKey {api_key}"}, timeout=30
    )
    if response.status_code in (400, 401, 403):
        raise GarminAuthError("Garmin afviste nøglen. Er den kopieret helt, og er den ikke udløbet eller slettet?")
    if not response.ok:
        raise RuntimeError(f"Garmin token request failed: {response.status_code}")
    token = response.text.strip()
    return token, _jwt_exp(token)


class GarminClient:
    def __init__(self, api_key: str, bearer: str | None = None, expires_at: int | None = None, on_token: TokenSaver | None = None):
        self._key = api_key
        self._bearer = bearer
        self._expires_at = expires_at or 0
        self._on_token = on_token

    def _token(self, force: bool = False) -> str:
        if force or not self._bearer or self._expires_at - REFRESH_WINDOW_SECONDS <= time.time():
            self._bearer, self._expires_at = exchange_key(self._key)
            if self._on_token:
                self._on_token(self._bearer, self._expires_at)
        return self._bearer

    def _get(self, path: str, params: dict | None = None, accept: str = "application/json"):
        for attempt in (0, 1):
            response = requests.get(
                f"{BASE_URL}{path}",
                params=params,
                headers={"Accept": accept, "Authorization": f"Bearer {self._token(force=attempt == 1)}"},
                timeout=60,
            )
            if response.status_code == 401 and attempt == 0:
                continue  # the token may have been revoked early: get a new one once
            return response
        return response  # pragma: no cover

    def _check(self, response, path: str):
        if response.status_code in (401, 403):
            raise GarminAuthError("Garmin afviser adgangen. Er nøglen udløbet eller slettet? Opret en ny under Mere → Mig.")
        if response.status_code == 429:
            raise RuntimeError("Garmin siger, at der er sendt for mange forespørgsler. Prøv igen om lidt.")
        if not response.ok:
            raise RuntimeError(f"Garmin {path} failed: {response.status_code} {response.text[:200]}")

    def search_activities(self, start: int = 0, limit: int = PAGE_SIZE, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
        path = "/activitylist-service/activities/search/activities"
        params: dict = {"start": start, "limit": limit}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        response = self._get(path, params)
        self._check(response, path)
        data = response.json()
        return data if isinstance(data, list) else []

    def download_activity(self, activity_id: int) -> bytes | None:
        """The activity file as ZIP bytes, or None if Garmin has no file for it."""
        path = f"/download-service/files/activity/{int(activity_id)}"
        response = self._get(path, accept="*/*")
        if response.status_code in (204, 404):
            return None
        self._check(response, path)
        content = response.content
        if len(content) > MAX_ZIP_BYTES:
            raise RuntimeError("Garmins aktivitetsfil er uventet stor")
        return content or None
