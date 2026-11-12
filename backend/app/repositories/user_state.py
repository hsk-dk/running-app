from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, user_id: int, key: str) -> dict | None:
    row = conn.execute(
        "SELECT value, updated_at FROM user_state WHERE user_id = ? AND key = ?", (user_id, key)
    ).fetchone()
    return dict(row) if row else None


def upsert(conn: sqlite3.Connection, user_id: int, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO user_state (user_id, key, value, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, key, value),
    )
