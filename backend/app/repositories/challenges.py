"""Daily challenges and their one count per day."""
from __future__ import annotations

import sqlite3


def list_active(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM challenges WHERE user_id = ? AND archived = 0 ORDER BY id", (user_id,)).fetchall()


def get(conn: sqlite3.Connection, user_id: int, challenge_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM challenges WHERE id = ? AND user_id = ?", (challenge_id, user_id)).fetchone()


def create(conn: sqlite3.Connection, user_id: int, values: dict) -> int:
    cur = conn.execute(
        "INSERT INTO challenges (user_id, name, unit, start_date, start_value, step, step_every_days, cap, rest_weekdays) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, values["name"], values["unit"], values["start_date"], values["start_value"], values["step"],
         values["step_every_days"], values["cap"], values["rest_weekdays"]),
    )
    return cur.lastrowid


def update_plan(conn: sqlite3.Connection, user_id: int, challenge_id: int, values: dict) -> bool:
    return conn.execute(
        "UPDATE challenges SET name = ?, unit = ?, start_value = ?, step = ?, step_every_days = ?, cap = ?, rest_weekdays = ? "
        "WHERE id = ? AND user_id = ? AND archived = 0",
        (values["name"], values["unit"], values["start_value"], values["step"], values["step_every_days"], values["cap"],
         values["rest_weekdays"], challenge_id, user_id),
    ).rowcount > 0


def archive(conn: sqlite3.Connection, user_id: int, challenge_id: int) -> bool:
    return conn.execute("UPDATE challenges SET archived = 1 WHERE id = ? AND user_id = ?", (challenge_id, user_id)).rowcount > 0


def logs(conn: sqlite3.Connection, challenge_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT day, count FROM challenge_logs WHERE challenge_id = ? ORDER BY day", (challenge_id,)).fetchall()


def set_log(conn: sqlite3.Connection, challenge_id: int, day: str, count: int) -> None:
    if count <= 0:
        conn.execute("DELETE FROM challenge_logs WHERE challenge_id = ? AND day = ?", (challenge_id, day))
        return
    conn.execute(
        "INSERT INTO challenge_logs (challenge_id, day, count) VALUES (?, ?, ?) "
        "ON CONFLICT(challenge_id, day) DO UPDATE SET count = excluded.count",
        (challenge_id, day, count),
    )
