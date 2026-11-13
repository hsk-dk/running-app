from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM garmin_accounts WHERE user_id = ?", (user_id,)).fetchone()


def upsert(conn: sqlite3.Connection, user_id: int, api_key: str, bearer: str | None = None, expires_at: int | None = None) -> None:
    conn.execute(
        """
        INSERT INTO garmin_accounts (user_id, api_key, bearer_token, token_expires_at) VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            api_key = excluded.api_key, bearer_token = excluded.bearer_token,
            token_expires_at = excluded.token_expires_at, connected_at = CURRENT_TIMESTAMP
        """,
        (user_id, api_key, bearer, expires_at),
    )


def update_token(conn: sqlite3.Connection, user_id: int, bearer: str, expires_at: int) -> None:
    conn.execute(
        "UPDATE garmin_accounts SET bearer_token = ?, token_expires_at = ? WHERE user_id = ?", (bearer, expires_at, user_id)
    )


def delete(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM garmin_accounts WHERE user_id = ?", (user_id,))
