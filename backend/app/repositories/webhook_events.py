from __future__ import annotations

import sqlite3


def find_duplicate(conn: sqlite3.Connection, key: tuple) -> sqlite3.Row | None:
    """key = (object_type, object_id, aspect_type, owner_id, event_time)."""
    return conn.execute(
        """
        SELECT id, processed FROM webhook_events
        WHERE provider = 'strava'
          AND object_type IS ? AND object_id IS ? AND aspect_type IS ?
          AND owner_id IS ? AND event_time IS ?
        ORDER BY id LIMIT 1
        """,
        key,
    ).fetchone()


def insert(
    conn: sqlite3.Connection,
    object_type,
    object_id,
    aspect_type,
    owner_id,
    subscription_id,
    event_time,
    payload_json: str,
    user_id: int | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO webhook_events (
            provider, object_type, object_id, aspect_type,
            owner_id, subscription_id, event_time, payload_json, user_id
        ) VALUES ('strava', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (object_type, object_id, aspect_type, owner_id, subscription_id, event_time, payload_json, user_id),
    )
    return cur.lastrowid


def mark_processed(conn: sqlite3.Connection, event_id: int) -> None:
    conn.execute(
        "UPDATE webhook_events SET processed = 1, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (event_id,),
    )


def count(conn: sqlite3.Connection, user_id: int | None = None) -> int:
    """Events stored. user_id=None counts every user's events."""
    if user_id is None:
        return conn.execute("SELECT COUNT(*) AS c FROM webhook_events").fetchone()["c"]
    return conn.execute("SELECT COUNT(*) AS c FROM webhook_events WHERE user_id = ?", (user_id,)).fetchone()["c"]


def latest(conn: sqlite3.Connection, user_id: int | None = None) -> dict | None:
    sql = "SELECT created_at, object_type, aspect_type FROM webhook_events"
    params: tuple = ()
    if user_id is not None:
        sql += " WHERE user_id = ?"
        params = (user_id,)
    row = conn.execute(sql + " ORDER BY id DESC LIMIT 1", params).fetchone()
    return dict(row) if row else None
