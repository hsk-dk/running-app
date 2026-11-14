"""Daily challenges for the signed-in person. Always their own: nobody else reads or writes a challenge."""
from __future__ import annotations

from datetime import date, timedelta

from app.db import get_conn
from app.domain import challenges as domain
from app.domain import timeutil
from app.errors import ConflictError, NotFoundError
from app.repositories import challenges as repo

MAX_ACTIVE = 10
LOG_WINDOW_DAYS = 14  # you can write today and the last two weeks, not rewrite the past


def _to_domain(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "unit": row["unit"],
        "start_date": date.fromisoformat(row["start_date"]),
        "start_value": row["start_value"],
        "step": row["step"],
        "step_every_days": row["step_every_days"],
        "cap": row["cap"],
        "rest_weekdays": [int(x) for x in row["rest_weekdays"].split(",") if x != ""],
    }


def _logs(conn, challenge_id: int) -> dict[date, int]:
    return {date.fromisoformat(r["day"]): r["count"] for r in repo.logs(conn, challenge_id)}


def _store(values: dict) -> dict:
    return {**values, "rest_weekdays": ",".join(str(x) for x in sorted(set(values["rest_weekdays"])))}


def _summary(conn, row, today) -> dict:
    s = domain.summary(_to_domain(row), _logs(conn, row["id"]), today)
    s["shared_today"] = today.isoformat() in repo.brag_days(conn, row["id"])
    return s


def list_for(user_id: int) -> list[dict]:
    today = timeutil.today()
    conn = get_conn()
    try:
        return [_summary(conn, r, today) for r in repo.list_active(conn, user_id)]
    finally:
        conn.close()


def _one(user_id: int, challenge_id: int) -> dict:
    today = timeutil.today()
    conn = get_conn()
    try:
        row = repo.get(conn, user_id, challenge_id)
        if row is None or row["archived"]:
            raise NotFoundError("Udfordringen findes ikke")
        return _summary(conn, row, today)
    finally:
        conn.close()


def create(user_id: int, values: dict) -> dict:
    conn = get_conn()
    try:
        if len(repo.list_active(conn, user_id)) >= MAX_ACTIVE:
            raise ConflictError(f"Du kan have op til {MAX_ACTIVE} udfordringer ad gangen")
        start = values.get("start_date") or timeutil.today()
        new_id = repo.create(conn, user_id, _store({**values, "start_date": start.isoformat()}))
        conn.commit()
    finally:
        conn.close()
    return _one(user_id, new_id)


def update(user_id: int, challenge_id: int, values: dict) -> dict:
    conn = get_conn()
    try:
        if not repo.update_plan(conn, user_id, challenge_id, _store(values)):
            raise NotFoundError("Udfordringen findes ikke")
        conn.commit()
    finally:
        conn.close()
    return _one(user_id, challenge_id)


def archive(user_id: int, challenge_id: int) -> None:
    conn = get_conn()
    try:
        if not repo.archive(conn, user_id, challenge_id):
            raise NotFoundError("Udfordringen findes ikke")
        conn.commit()
    finally:
        conn.close()


def log(user_id: int, challenge_id: int, count: int, day: date | None) -> dict:
    today = timeutil.today()
    day = day or today
    if day > today:
        raise ConflictError("Du kan ikke skrive en dag, der ikke er kommet endnu")
    if day < today - timedelta(days=LOG_WINDOW_DAYS):
        raise ConflictError(f"Du kan kun rette de seneste {LOG_WINDOW_DAYS} dage")
    conn = get_conn()
    try:
        row = repo.get(conn, user_id, challenge_id)
        if row is None or row["archived"]:
            raise NotFoundError("Udfordringen findes ikke")
        repo.set_log(conn, challenge_id, day.isoformat(), count)
        repo.delete_brag(conn, challenge_id, day.isoformat())  # a changed number is not what was shown: share it again if you like
        conn.commit()
    finally:
        conn.close()
    return _one(user_id, challenge_id)


def share(user_id: int, challenge_id: int, day: date | None) -> dict:
    """Show the family a day's number. Only a day you actually did, and only a goal you reached or a new best."""
    today = timeutil.today()
    day = day or today
    if day > today or day < today - timedelta(days=LOG_WINDOW_DAYS):
        raise ConflictError("Du kan kun dele i dag og de seneste dage")
    conn = get_conn()
    try:
        row = repo.get(conn, user_id, challenge_id)
        if row is None or row["archived"]:
            raise NotFoundError("Udfordringen findes ikke")
        ch, logs = _to_domain(row), _logs(conn, challenge_id)
        count = logs.get(day, 0)
        target = domain.target_for(ch, day)
        if count <= 0 or not ((target is not None and count >= target) or day in domain.best_days(ch, logs)):
            raise ConflictError("Du kan dele en dag, hvor du klarede målet eller satte ny rekord")
        repo.add_brag(conn, challenge_id, day.isoformat())
        conn.commit()
    finally:
        conn.close()
    return _one(user_id, challenge_id)


def unshare(user_id: int, challenge_id: int, day: date | None) -> dict:
    day = day or timeutil.today()
    conn = get_conn()
    try:
        row = repo.get(conn, user_id, challenge_id)
        if row is None or row["archived"]:
            raise NotFoundError("Udfordringen findes ikke")
        repo.delete_brag(conn, challenge_id, day.isoformat())
        conn.commit()
    finally:
        conn.close()
    return _one(user_id, challenge_id)


def recent_brags() -> list[dict]:
    """What people chose to show the family, with the number, from the last three weeks."""
    since = (timeutil.today() - timedelta(days=21)).isoformat()
    conn = get_conn()
    try:
        rows = repo.recent_brags(conn, since)
    finally:
        conn.close()
    return [{"user_id": r["user_id"], "challenge": r["name"], "unit": r["unit"], "count": r["count"], "date": r["day"]} for r in rows]


def for_family(user_id: int) -> dict:
    """For a parent looking at a child, and for milestones: how many days were done, never the numbers themselves."""
    today = timeutil.today()
    conn = get_conn()
    try:
        rows = repo.list_active(conn, user_id)
        items, milestones = [], []
        for r in rows:
            ch = _to_domain(r)
            logs = _logs(conn, r["id"])
            s = domain.summary(ch, logs, today)
            p = s["progress"]
            items.append({
                "name": s["name"], "unit": s["unit"], "done_week": s["done_week"], "planned_week": s["planned_week"], "streak_days": s["streak_days"],
                "first_count": p["first_count"] if p else None, "recent_best": p["recent_best"] if p else None, "weeks": p["weeks"] if p else None,
            })
            milestones += [m for m in domain.milestone_dates(ch, logs, today) if today - m["date"] <= timedelta(days=21)]
            milestones += domain.improvement_milestones(ch, logs, today)
    finally:
        conn.close()
    return {"items": items, "milestones": [{**m, "date": m["date"].isoformat()} for m in milestones]}
