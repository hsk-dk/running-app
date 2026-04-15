from __future__ import annotations

import requests
from app.config import settings

TOKEN_URL = "https://www.strava.com/oauth/token"
BASE_URL = "https://www.strava.com/api/v3"


class StravaClient:
    def __init__(self):
        self._access_token = None

    def refresh_access_token(self) -> str:
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": settings.STRAVA_CLIENT_ID,
                "client_secret": settings.STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": settings.STRAVA_REFRESH_TOKEN,
            },
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                f"Strava token refresh failed: {response.status_code} {response.text}"
            )

        payload = response.json()
        self._access_token = payload["access_token"]
        return self._access_token

    def headers(self) -> dict[str, str]:
        if not self._access_token:
            self.refresh_access_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    def get_activities(self, page: int = 1, per_page: int = 50, after_epoch: int | None = None):
        params = {"page": page, "per_page": per_page}
        if after_epoch is not None:
            params["after"] = after_epoch

        response = requests.get(
            f"{BASE_URL}/athlete/activities",
            headers=self.headers(),
            params=params,
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                f"Strava get_activities failed: {response.status_code} {response.text}"
            )

        return response.json()

    def create_push_subscription(self):
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
            raise RuntimeError(
                f"Strava create_push_subscription failed: {response.status_code} {response.text}"
            )

        return response.json()

    def list_push_subscriptions(self):
        response = requests.get(
            f"{BASE_URL}/push_subscriptions",
            params={
                "client_id": settings.STRAVA_CLIENT_ID,
                "client_secret": settings.STRAVA_CLIENT_SECRET,
            },
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                f"Strava list_push_subscriptions failed: {response.status_code} {response.text}"
            )

        return response.json()
