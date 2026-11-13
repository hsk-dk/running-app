from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM strava_accounts WHERE user_id = ?", (user_id,)).fetchone()


def get_by_athlete(conn: sqlite3.Connection, athlete_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM strava_accounts WHERE athlete_id = ?", (str(athlete_id),)).fetchone()


def count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM strava_accounts").fetchone()[0]


def upsert(
    conn: sqlite3.Connection,
    user_id: int,
    athlete_id: str,
    refresh_token: str,
    access_token: str | None = None,
    access_expires_at: int | None = None,
    scope: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO strava_accounts (user_id, athlete_id, refresh_token, access_token, access_expires_at, scope)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            athlete_id = excluded.athlete_id,
            refresh_token = excluded.refresh_token,
            access_token = excluded.access_token,
            access_expires_at = excluded.access_expires_at,
            scope = excluded.scope,
            connected_at = CURRENT_TIMESTAMP
        """,
        (user_id, str(athlete_id), refresh_token, access_token, access_expires_at, scope),
    )


def update_tokens(
    conn: sqlite3.Connection, user_id: int, refresh_token: str, access_token: str | None, access_expires_at: int | None
) -> None:
    conn.execute(
        "UPDATE strava_accounts SET refresh_token = ?, access_token = ?, access_expires_at = ? WHERE user_id = ?",
        (refresh_token, access_token, access_expires_at, user_id),
    )


def delete(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM strava_accounts WHERE user_id = ?", (user_id,))
