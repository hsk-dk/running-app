"""Kilometre splits for one run: fetched from Strava the first time they are asked for, then kept."""
from __future__ import annotations

import json
import logging

from app.db import get_conn
from app.domain.splits import parse_splits
from app.errors import NotConnectedError, NotFoundError
from app.repositories import activities as activity_repo
from app.services import garmin_service, sync_service

log = logging.getLogger(__name__)


def get_splits(user_id: int, activity_id: int) -> dict:
    conn = get_conn()
    try:
        row = activity_repo.get(conn, user_id, activity_id)
        if row is None or row["sport_type"] != "Run":
            raise NotFoundError(f"Activity {activity_id} not found")
        cached = row["splits_json"]
    finally:
        conn.close()

    if cached is not None:
        return {"available": True, "splits": json.loads(cached)}

    if row["garmin_id"] is not None and row["fit_status"] != "none":
        # The watch's own file gives splits for every kind of run, treadmill included.
        if row["fit_status"] is None and garmin_service.read_fit(user_id, row) is None:
            return {"available": False, "splits": []}
        conn = get_conn()
        try:
            fresh = activity_repo.get(conn, user_id, activity_id)
        finally:
            conn.close()
        if fresh is not None and fresh["splits_json"] is not None:
            return {"available": True, "splits": json.loads(fresh["splits_json"])}
        return {"available": True, "splits": []}

    try:
        detailed = sync_service.client_for(user_id).get_activity(activity_id)
    except NotConnectedError:
        return {"available": False, "splits": []}
    except Exception:  # Strava down, rate limit, revoked token: the run page must still work
        log.warning("Could not fetch splits for activity %s", activity_id, exc_info=True)
        return {"available": False, "splits": []}

    if detailed is None:  # deleted on Strava
        return {"available": False, "splits": []}

    splits = parse_splits(detailed.get("splits_metric"))
    conn = get_conn()
    try:
        activity_repo.set_splits_json(conn, user_id, activity_id, json.dumps(splits))
        conn.commit()
    finally:
        conn.close()
    return {"available": True, "splits": splits}
