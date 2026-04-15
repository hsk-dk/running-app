from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from app.db import get_conn
from app.strava import StravaClient
from app.admin_status import set_state, clear_last_error


def get_last_synced_start_date():
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key = 'last_synced_start_date'"
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_last_synced_start_date(value: str):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO sync_state (key, value, updated_at)
            VALUES ('last_synced_start_date', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (value,),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_activity(activity: dict):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO activities (
                id,
                name,
                sport_type,
                start_date,
                timezone_name,
                distance_m,
                moving_time_s,
                elapsed_time_s,
                total_elevation_gain,
                average_speed,
                max_speed,
                average_heartrate,
                max_heartrate,
                average_cadence,
                raw_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                sport_type = excluded.sport_type,
                start_date = excluded.start_date,
                timezone_name = excluded.timezone_name,
                distance_m = excluded.distance_m,
                moving_time_s = excluded.moving_time_s,
                elapsed_time_s = excluded.elapsed_time_s,
                total_elevation_gain = excluded.total_elevation_gain,
                average_speed = excluded.average_speed,
                max_speed = excluded.max_speed,
                average_heartrate = excluded.average_heartrate,
                max_heartrate = excluded.max_heartrate,
                average_cadence = excluded.average_cadence,
                raw_json = excluded.raw_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                activity["id"],
                activity.get("name"),
                activity.get("sport_type"),
                activity.get("start_date"),
                activity.get("timezone"),
                activity.get("distance"),
                activity.get("moving_time"),
                activity.get("elapsed_time"),
                activity.get("total_elevation_gain"),
                activity.get("average_speed"),
                activity.get("max_speed"),
                activity.get("average_heartrate"),
                activity.get("max_heartrate"),
                activity.get("average_cadence"),
                json.dumps(activity, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def ingest_recent(pages: int = 3):
    client = StravaClient()
    last_synced = get_last_synced_start_date()
    after_epoch = None

    if last_synced:
        dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00")) - timedelta(days=2)
        after_epoch = int(dt.replace(tzinfo=timezone.utc).timestamp())

    newest_seen = None
    upserted = 0

    for page in range(1, pages + 1):
        activities = client.get_activities(page=page, per_page=50, after_epoch=after_epoch)
        if not activities:
            break

        for activity in activities:
            if activity.get("sport_type") != "Run":
                continue

            upsert_activity(activity)
            upserted += 1

            start_date = activity.get("start_date")
            if start_date:
                dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if newest_seen is None or dt > newest_seen:
                    newest_seen = dt

    if newest_seen is not None:
        set_last_synced_start_date(
            newest_seen.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )

    result = {"upserted": upserted}
    set_state("last_sync_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    set_state("last_ingest_result", json.dumps(result, ensure_ascii=False))
    clear_last_error()
    return result


def ingest_latest_window(hours_back: int = 72):
    client = StravaClient()
    after_dt = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    after_epoch = int(after_dt.timestamp())

    upserted = 0
    activities = client.get_activities(page=1, per_page=100, after_epoch=after_epoch)

    for activity in activities:
        if activity.get("sport_type") != "Run":
            continue
        upsert_activity(activity)
        upserted += 1

    result = {"upserted": upserted, "window_hours": hours_back}
    set_state("last_sync_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    set_state("last_ingest_result", json.dumps(result, ensure_ascii=False))
    clear_last_error()
    return result
