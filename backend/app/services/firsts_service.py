"""First times for the signed-in person, and the recent ones for family members to cheer on."""
from __future__ import annotations

from app.db import get_conn
from app.domain import firsts, timeutil
from app.repositories import activities as activity_repo

NEW_DAYS = 7
FAMILY_DAYS = 21


def _runs(user_id: int):
    conn = get_conn()
    try:
        rows = activity_repo.list_runs_for_metrics(conn, user_id)
    finally:
        conn.close()
    out = []
    for row in rows:
        day = timeutil.activity_local_date(row)
        if day is not None:
            out.append((day, float(row["distance_m"] or 0) / 1000.0))
    return out


def _iso(item: dict) -> dict:
    return {**item, "date": item["date"].isoformat()}


def for_user(user_id: int) -> dict:
    today = timeutil.today()
    runs = _runs(user_id)
    done = firsts.achieved(runs)
    fresh = {a["key"] for a in firsts.recent(done, today, NEW_DAYS)}
    return {
        "achieved": [{**_iso(a), "is_new": a["key"] in fresh} for a in done],
        "next": firsts.next_up(runs, today),
    }


def recent_for_family(user_id: int) -> list[dict]:
    """What this person reached lately: only the label and the day, never distances or times."""
    today = timeutil.today()
    done = firsts.achieved(_runs(user_id))
    # the labels are for "Anna: ..." in a list, so the personal "Dit første løb" becomes "Første løb"
    return [
        {"key": a["key"], "label": "Første løb" if a["key"] == "first_run" else a["label"], "date": a["date"].isoformat()}
        for a in firsts.recent(done, today, FAMILY_DAYS)
    ]
