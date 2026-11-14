from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_by_external_id(conn: sqlite3.Connection, external_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE external_id = ?", (external_id,)).fetchone()


def list_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM users ORDER BY id").fetchall()


def create(conn: sqlite3.Connection, external_id: str, username: str, display_name: str | None, role: str) -> int:
    cur = conn.execute(
        "INSERT INTO users (external_id, username, display_name, role, last_seen_at) "
        "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (external_id, username, display_name, role),
    )
    return cur.lastrowid


def update_identity(
    conn: sqlite3.Connection, user_id: int, username: str, display_name: str | None, role: str
) -> None:
    """Called on every request from the identity provider; keeps name and role current."""
    conn.execute(
        "UPDATE users SET username = ?, display_name = ?, role = ?, last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
        (username, display_name, role, user_id),
    )


def set_sharing_level(conn: sqlite3.Connection, user_id: int, level: str) -> None:
    conn.execute("UPDATE users SET sharing_level = ? WHERE id = ?", (level, user_id))


def set_child(conn: sqlite3.Connection, user_id: int, is_child: bool) -> None:
    conn.execute("UPDATE users SET is_child = ? WHERE id = ?", (1 if is_child else 0, user_id))


def set_display_name(conn: sqlite3.Connection, user_id: int, display_name: str | None) -> None:
    conn.execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id))


def set_external_id(conn: sqlite3.Connection, user_id: int, external_id: str) -> None:
    """Used once, when the first person to sign in takes over the data from before users existed."""
    conn.execute("UPDATE users SET external_id = ? WHERE id = ?", (external_id, user_id))
