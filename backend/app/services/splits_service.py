"""Kilometre splits for one run: read from the watch's FIT file the first time they are asked for, then kept."""
from __future__ import annotations

import json

from app.db import get_conn
from app.errors import NotFoundError
from app.repositories import activities as activity_repo
from app.services import garmin_service


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

    # A run without a Garmin link and without splits already stored (an older run from Strava or Smashrun) has none to show.
    return {"available": True, "splits": []}
