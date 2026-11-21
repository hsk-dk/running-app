"""Fetches new runs and the plan for everyone with a connected source, on a timer, so nobody has to press a button.

Garmin's personal API has no push (no webhook), so the app asks. A failing person is asked less and less often (up to every six
hours) instead of every round, and a person whose sync is already running is skipped.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from app.config import settings
from app.errors import NotConnectedError
from app.services import admin_service, user_service

logger = logging.getLogger(__name__)

MAX_BACKOFF_SECONDS = 6 * 3600
FIRST_RUN_DELAY_SECONDS = 60  # let the app settle after a start before the first round


class AutoSync:
    def __init__(
        self,
        interval_seconds: float,
        run: Callable[..., object] = admin_service.run_ingest,
        users: Callable[[], list[int]] = user_service.all_user_ids,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.interval = interval_seconds
        self._run = run
        self._users = users
        self._clock = clock
        self._failures: dict[int, tuple[int, float]] = {}  # user -> (consecutive failures, do not ask before)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _due(self, user_id: int, now: float) -> bool:
        failed = self._failures.get(user_id)
        return failed is None or now >= failed[1]

    def _note_failure(self, user_id: int, now: float) -> None:
        count = self._failures.get(user_id, (0, 0.0))[0] + 1
        self._failures[user_id] = (count, now + min(MAX_BACKOFF_SECONDS, self.interval * (2 ** count)))

    def tick(self) -> dict[str, list[int]]:
        """One round: everybody who is due is synced, one at a time. Returns who was synced, skipped, failed or had nothing to sync."""
        done: dict[str, list[int]] = {"synced": [], "skipped": [], "failed": [], "nothing": []}
        for user_id in self._users():
            now = self._clock()
            if not self._due(user_id, now):
                done["skipped"].append(user_id)
                continue
            try:
                result = self._run(user_id, wait=False)
            except NotConnectedError:
                done["nothing"].append(user_id)  # no source connected: nothing to do, and not a failure
                continue
            except Exception as exc:  # one person's trouble never stops the round
                logger.warning("Automatic sync failed for user %s: %s", user_id, exc)
                self._note_failure(user_id, now)
                done["failed"].append(user_id)
                continue
            if result is None:
                done["skipped"].append(user_id)  # their sync is already running
                continue
            self._failures.pop(user_id, None)
            done["synced"].append(user_id)
        return done

    def _loop(self) -> None:
        if self._stop.wait(FIRST_RUN_DELAY_SECONDS):
            return
        while True:
            try:
                self.tick()
            except Exception:  # the loop must never die
                logger.exception("Automatic sync round failed")
            if self._stop.wait(self.interval):
                return

    def start(self) -> None:
        if self.interval <= 0 or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="auto-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None


def from_settings() -> AutoSync:
    return AutoSync(max(0, settings.SYNC_INTERVAL_MINUTES) * 60)
