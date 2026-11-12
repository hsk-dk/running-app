from __future__ import annotations

import time
from typing import Callable
from urllib.parse import urlencode

import requests

from app.config import settings

TOKEN_URL = "https://www.strava.com/oauth/token"
AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
BASE_URL = "https://www.strava.com/api/v3"
SCOPE = "read,activity:read_all"

# Called with (refresh_token, access_token, expires_at) whenever Strava hands out new tokens.
TokenSaver = Callable[[str, str, int], None]


def authorize_url(redirect_uri: str, state: str) -> str:
    return AUTHORIZE_URL + "?" + urlencode(
        {
            "client_id": settings.STRAVA_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": SCOPE,
            "state": state,
        }
    )


def exchange_code(code: str) -> dict:
    """Trade the one-time code from the Strava redirect for tokens and the athlete."""
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": settings.STRAVA_CLIENT_ID,
            "client_secret": settings.STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Strava code exchange failed: {response.status_code}")
    return response.json()


class StravaClient:
    """One athlete's access. Strava rotates the refresh token, so new tokens are saved through `on_tokens`."""

    def __init__(
        self,
        refresh_token: str,
        access_token: str | None = None,
        access_expires_at: int | None = None,
        on_tokens: TokenSaver | None = None,
    ):
        self._refresh_token = refresh_token
        self._access_token = access_token
        self._expires_at = access_expires_at or 0
        self._on_tokens = on_tokens

    def refresh_access_token(self) -> str:
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": settings.STRAVA_CLIENT_ID,
                "client_secret": settings.STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
            timeout=30,
        )
        if not response.ok:
            raise RuntimeError(f"Strava token refresh failed: {response.status_code} {response.text}")

        payload = response.json()
        self._access_token = payload["access_token"]
        self._expires_at = int(payload.get("expires_at", 0))
        self._refresh_token = payload.get("refresh_token", self._refresh_token)
        if self._on_tokens:
            self._on_tokens(self._refresh_token, self._access_token, self._expires_at)
        return self._access_token

    def headers(self) -> dict[str, str]:
        if not self._access_token or self._expires_at - 60 <= time.time():
            self.refresh_access_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    def get_activities(self, page: int = 1, per_page: int = 50, after_epoch: int | None = None):
        params = {"page": page, "per_page": per_page}
        if after_epoch is not None:
            params["after"] = after_epoch

        response = requests.get(f"{BASE_URL}/athlete/activities", headers=self.headers(), params=params, timeout=30)
        if not response.ok:
            raise RuntimeError(f"Strava get_activities failed: {response.status_code} {response.text}")
        return response.json()

    def get_activity(self, activity_id: int):
        response = requests.get(f"{BASE_URL}/activities/{int(activity_id)}", headers=self.headers(), timeout=30)
        if response.status_code == 404:
            return None
        if not response.ok:
            raise RuntimeError(f"Strava get_activity failed: {response.status_code} {response.text}")
        return response.json()


# ---- app-level calls (use the app's own client id and secret, not an athlete's token) ------------------

def create_push_subscription():
    response = requests.post(
        f"{BASE_URL}/push_subscriptions",
        data={
            "client_id": settings.STRAVA_CLIENT_ID,
            "client_secret": settings.STRAVA_CLIENT_SECRET,
            "callback_url": settings.STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL,
            "verify_token": settings.STRAVA_VERIFY_TOKEN,
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Strava create_push_subscription failed: {response.status_code} {response.text}")
    return response.json()


def list_push_subscriptions():
    response = requests.get(
        f"{BASE_URL}/push_subscriptions",
        params={"client_id": settings.STRAVA_CLIENT_ID, "client_secret": settings.STRAVA_CLIENT_SECRET},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Strava list_push_subscriptions failed: {response.status_code} {response.text}")
    return response.json()
