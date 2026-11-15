"""Stars and the family's reward. A star rewards effort (an active day, a challenge day), never speed or distance."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.db import get_conn
from app.domain import challenges as challenge_domain
from app.domain import stars as domain
from app.domain import timeutil
from app.errors import ConflictError, ForbiddenError, NotFoundError
from app.repositories import activities as activity_repo
from app.repositories import challenges as challenge_repo
from app.repositories import stars as repo
from app.services import user_service
from app.services.user_service import CurrentUser

BONUS_PER_DAY_MAX = 3


def _challenge_days(conn, user_id: int, today: date) -> set[date]:
    out: set[date] = set()
    for row in challenge_repo.all_for_user(conn, user_id):
        ch = {
            "id": row["id"], "name": row["name"], "unit": row["unit"], "start_date": date.fromisoformat(row["start_date"]),
            "start_value": row["start_value"], "step": row["step"], "step_every_days": row["step_every_days"], "cap": row["cap"],
            "rest_weekdays": [int(x) for x in row["rest_weekdays"].split(",") if x != ""],
        }
        logs = {date.fromisoformat(r["day"]): r["count"] for r in challenge_repo.logs(conn, row["id"])}
        out |= challenge_domain.done_days(ch, logs, today)
    return out


def _active_days(conn, user_id: int) -> set[date]:
    seconds: dict[date, float] = defaultdict(float)
    for row in activity_repo.list_durations(conn, user_id):
        day = timeutil.activity_local_date(row)
        if day is not None:
            seconds[day] += float(row["moving_time_s"] or 0)
    return domain.active_days(seconds)


def stars_of(user_id: int) -> tuple[dict[date, int], dict[date, int]]:
    """(earned, bonus): the stars of each day for one person."""
    today = timeutil.today()
    conn = get_conn()
    try:
        earned = domain.earned(_active_days(conn, user_id), _challenge_days(conn, user_id, today))
        bonus = {date.fromisoformat(r["day"]): r["n"] for r in repo.bonus_rows(conn, user_id)}
    finally:
        conn.close()
    return earned, bonus


def mine(user_id: int) -> dict:
    earned, bonus = stars_of(user_id)
    return {"total": domain.total(earned, bonus), "week": domain.week_of(earned, bonus, timeutil.today())}


def _counts(u: CurrentUser) -> bool:
    """Who is in the family's stars: everyone who shares, and children (their parents are in the loop anyway)."""
    return u.sharing_level != "private" or u.is_child


def family_pace() -> dict:
    """How fast the family earns stars, whether or not there is a reward yet: people, stars a week, and whether it is only a guess."""
    window_from = timeutil.today() - timedelta(days=domain.RATE_DAYS - 1)
    in_window = 0
    people = 0
    for u in user_service.list_users():
        if _counts(u):
            people += 1
            earned, bonus = stars_of(u.id)
            in_window += domain.total(earned, bonus, window_from)
    return {"people": people, **domain.pace(in_window, people)}


def reward_progress() -> dict | None:
    """The family's reward with the stars of everyone together. Nobody's own part is shown."""
    conn = get_conn()
    try:
        row = repo.active_reward(conn)
        recent = [{"name": r["name"], "cost": r["cost"], "date": r["redeemed_on"]} for r in repo.redeemed(conn)]
    finally:
        conn.close()
    if row is None:
        return None
    since = date.fromisoformat(row["since_day"])
    stars = row["carry"]
    for u in user_service.list_users():
        if _counts(u):
            earned, bonus = stars_of(u.id)
            stars += domain.total(earned, bonus, since)
    state = domain.reward_state(row["cost"], stars)
    rate = family_pace()
    return {
        "id": row["id"], "name": row["name"], **state, "recent": recent,
        "people": rate["people"], "per_week": rate["per_week"], "estimated": rate["estimated"],
        "weeks_left": domain.weeks_left(state["remaining"], rate["per_week"]),
    }


def _admin(user: CurrentUser) -> None:
    if not user.is_admin:
        raise ForbiddenError("Kun en forælder kan ændre familiens belønning")


def set_reward(admin: CurrentUser, name: str, cost: int) -> dict:
    _admin(admin)
    conn = get_conn()
    try:
        row = repo.active_reward(conn)
        if row is None:
            repo.create_reward(conn, name.strip(), cost, timeutil.today().isoformat())
        else:
            repo.update_reward(conn, row["id"], name.strip(), cost)
        conn.commit()
    finally:
        conn.close()
    return reward_progress()  # type: ignore[return-value]


def clear_reward(admin: CurrentUser) -> None:
    _admin(admin)
    conn = get_conn()
    try:
        repo.delete_active_reward(conn)
        conn.commit()
    finally:
        conn.close()


def redeem(admin: CurrentUser) -> dict:
    """A parent says the reward has been given. Anything beyond the cost carries over to the next one, which starts tomorrow."""
    _admin(admin)
    current = reward_progress()
    if current is None:
        raise NotFoundError("Der er ingen belønning at indløse")
    if not current["reached"]:
        raise ConflictError("Der mangler stadig stjerner")
    today = timeutil.today()
    conn = get_conn()
    try:
        row = repo.active_reward(conn)
        repo.close_reward(conn, row["id"], today.isoformat())
        repo.create_reward(conn, row["name"], row["cost"], (today + timedelta(days=1)).isoformat(), max(0, current["stars"] - row["cost"]))
        conn.commit()
    finally:
        conn.close()
    return reward_progress()  # type: ignore[return-value]


def give_bonus(admin: CurrentUser, user_id: int, note: str | None) -> dict:
    """A parent gives someone a bonus star for effort that is not measured. At most three a day for one person."""
    _admin(admin)
    if not any(u.id == user_id for u in user_service.list_users()):
        raise NotFoundError("Personen findes ikke")
    today = timeutil.today().isoformat()
    conn = get_conn()
    try:
        if repo.bonus_count_on(conn, user_id, today) >= BONUS_PER_DAY_MAX:
            raise ConflictError(f"Højst {BONUS_PER_DAY_MAX} bonusstjerner om dagen til samme person")
        repo.add_bonus(conn, user_id, today, admin.id, (note or "").strip()[:80] or None)
        conn.commit()
    finally:
        conn.close()
    return mine(user_id)
