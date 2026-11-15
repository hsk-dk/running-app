"""Bonus stars and the family's reward. SQL only."""
from __future__ import annotations

import sqlite3


def bonus_rows(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT day, COUNT(*) AS n FROM star_bonus WHERE user_id = ? GROUP BY day", (user_id,)).fetchall()


def bonus_count_on(conn: sqlite3.Connection, user_id: int, day: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM star_bonus WHERE user_id = ? AND day = ?", (user_id, day)).fetchone()[0]


def add_bonus(conn: sqlite3.Connection, user_id: int, day: str, given_by: int, note: str | None) -> None:
    conn.execute("INSERT INTO star_bonus (user_id, day, given_by, note) VALUES (?, ?, ?, ?)", (user_id, day, given_by, note))


def active_reward(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM family_rewards WHERE redeemed_on IS NULL ORDER BY id DESC LIMIT 1").fetchone()


def create_reward(conn: sqlite3.Connection, name: str, cost: int, since_day: str, carry: int = 0) -> int:
    return conn.execute(
        "INSERT INTO family_rewards (name, cost, since_day, carry) VALUES (?, ?, ?, ?)", (name, cost, since_day, carry)
    ).lastrowid


def update_reward(conn: sqlite3.Connection, reward_id: int, name: str, cost: int) -> None:
    conn.execute("UPDATE family_rewards SET name = ?, cost = ? WHERE id = ? AND redeemed_on IS NULL", (name, cost, reward_id))


def close_reward(conn: sqlite3.Connection, reward_id: int, day: str) -> None:
    conn.execute("UPDATE family_rewards SET redeemed_on = ? WHERE id = ?", (day, reward_id))


def delete_active_reward(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM family_rewards WHERE redeemed_on IS NULL")


def redeemed(conn: sqlite3.Connection, limit: int = 5) -> list[sqlite3.Row]:
    return conn.execute("SELECT name, cost, redeemed_on FROM family_rewards WHERE redeemed_on IS NOT NULL ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
