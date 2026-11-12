from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, key: str) -> dict | None:
    row = conn.execute(
        "SELECT value, updated_at FROM sync_state WHERE key = ?", (key,)
    ).fetchone()
    return dict(row) if row else None


def upsert(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO sync_state (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, value),
    )
