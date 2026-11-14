"""Settings that belong to the whole app, not to one person (for example the family's monthly goal)."""
from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def upsert(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO sync_state (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (key, value),
    )


def delete(conn: sqlite3.Connection, key: str) -> None:
    conn.execute("DELETE FROM sync_state WHERE key = ?", (key,))
