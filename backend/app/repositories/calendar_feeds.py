from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM calendar_feeds WHERE user_id = ?", (user_id,)).fetchone()


def upsert(conn: sqlite3.Connection, user_id: int, url: str, kind: str = "runna") -> None:
    conn.execute(
        """
        INSERT INTO calendar_feeds (user_id, kind, url) VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET kind = excluded.kind, url = excluded.url, connected_at = CURRENT_TIMESTAMP
        """,
        (user_id, kind, url),
    )


def delete(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM calendar_feeds WHERE user_id = ?", (user_id,))
