"""The shelf of badges for the signed-in person: what they have earned and what is ahead."""
from __future__ import annotations

from datetime import date

from app.db import get_conn
from app.domain import badges as domain
from app.domain import challenges as challenge_domain
from app.domain import firsts, timeutil
from app.repositories import challenges as challenge_repo
from app.services import firsts_service, star_service


def _challenge_inputs(user_id: int, today: date) -> dict:
    streaks: dict[int, date] = {}
    best: date | None = None
    double: date | None = None
    conn = get_conn()
    try:
        for row in challenge_repo.all_for_user(conn, user_id):
            ch = {
                "id": row["id"], "name": row["name"], "unit": row["unit"], "start_date": date.fromisoformat(row["start_date"]),
                "start_value": row["start_value"], "step": row["step"], "step_every_days": row["step_every_days"], "cap": row["cap"],
                "rest_weekdays": [int(x) for x in row["rest_weekdays"].split(",") if x != ""],
            }
            logs = {date.fromisoformat(r["day"]): r["count"] for r in challenge_repo.logs(conn, row["id"])}
            for n, day in challenge_domain.streak_dates(ch, logs, today).items():
                if n not in streaks or day < streaks[n]:
                    streaks[n] = day
            days = challenge_domain.best_days(ch, logs)
            if days and (best is None or days[0] < best):
                best = days[0]
            doubled = challenge_domain.doubled_on(ch, logs)
            if doubled and (double is None or doubled < double):
                double = doubled
    finally:
        conn.close()
    return {"streaks": streaks, "best": best, "double": double}


def for_user(user_id: int) -> dict:
    today = timeutil.today()
    runs = firsts_service._runs(user_id)
    done = [{"key": a["key"], "date": a["date"]} for a in firsts.achieved(runs)]
    earned, bonus = star_service.stars_of(user_id)
    by_day = {d: earned.get(d, 0) + bonus.get(d, 0) for d in set(earned) | set(bonus)}
    shelf = domain.shelf(done, _challenge_inputs(user_id, today), by_day, today)
    return {
        "earned": [{**b, "date": b["date"].isoformat()} for b in shelf["earned"]],
        "ahead": shelf["ahead"],
        "total": shelf["total"],
    }
