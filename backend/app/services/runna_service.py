"""A person's Runna plan, read from their Runna calendar link: planned runs, and Runna's names for their runs."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app import runna
from app.db import get_conn
from app.domain import runna as domain
from app.domain import timeutil
from app.domain.statuses import STATUS_PLANLAGT
from app.errors import ConflictError, NotConnectedError
from app.repositories import activities as activity_repo
from app.repositories import calendar_feeds, user_state
from app.repositories import planned_runs as plan_repo

logger = logging.getLogger(__name__)

SOURCE = "runna"
NAME_WINDOW_SECONDS = 300


def status(user_id: int) -> dict:
    conn = get_conn()
    try:
        feed = calendar_feeds.get(conn, user_id)
        last = user_state.get(conn, user_id, "runna_last_sync_at")
        error = user_state.get(conn, user_id, "runna_last_error")
        return {
            "connected": feed is not None,
            "last_sync_at": last["value"] if last and last["value"] else None,
            "last_error": error["value"] if error and error["value"] else None,
        }
    finally:
        conn.close()


def connect(user_id: int, url: str) -> dict:
    """Check the link really is a readable Runna calendar before saving it."""
    try:
        url = runna.check_url(url)
        text = runna.fetch(url)
    except runna.RunnaLinkError as exc:
        raise ConflictError(str(exc)) from exc
    domain.parse_events(text)  # raises nothing: an empty calendar is fine (a new plan may not have started)
    conn = get_conn()
    try:
        calendar_feeds.upsert(conn, user_id, url)
        conn.commit()
    finally:
        conn.close()
    return status(user_id)


def disconnect(user_id: int) -> dict:
    conn = get_conn()
    try:
        calendar_feeds.delete(conn, user_id)
        conn.commit()
    finally:
        conn.close()
    return status(user_id)


def _set_state(conn, user_id: int, key: str, value: str) -> None:
    user_state.upsert(conn, user_id, key, value)


def sync(user_id: int) -> dict:
    """Read the calendar, keep the plan in step with it, and give runs Runna's names."""
    conn = get_conn()
    try:
        feed = calendar_feeds.get(conn, user_id)
    finally:
        conn.close()
    if feed is None:
        raise NotConnectedError("Runna er ikke forbundet")

    try:
        events = domain.parse_events(runna.fetch(feed["url"]))
    except runna.RunnaLinkError as exc:
        _record_error(user_id, str(exc))
        raise ConflictError(str(exc)) from exc
    except Exception as exc:
        _record_error(user_id, str(exc))
        raise

    result = _import_plan(user_id, domain.planned_runs(events))
    result["named"] = _name_runs(user_id, domain.completed_runs(events))

    conn = get_conn()
    try:
        _set_state(conn, user_id, "runna_last_sync_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        _set_state(conn, user_id, "runna_last_error", "")
        _set_state(conn, user_id, "runna_last_result", json.dumps(result, ensure_ascii=False))
        conn.commit()
    finally:
        conn.close()
    return {"source": "runna", **result}


def _record_error(user_id: int, message: str) -> None:
    conn = get_conn()
    try:
        _set_state(conn, user_id, "runna_last_error", message)
        conn.commit()
    finally:
        conn.close()


def _import_plan(user_id: int, items: list[dict]) -> dict:
    added = updated = skipped = 0
    conn = get_conn()
    try:
        for item in items:
            existing = plan_repo.get_by_external_uid(conn, user_id, item["external_uid"])
            fields = {k: item[k] for k in ("planned_date", "session_type", "target_type", "target_value", "notes")}
            if existing is not None:
                plan_repo.update_imported(conn, user_id, existing["id"], **fields)
                updated += 1
            elif plan_repo.count_manual_on_date(conn, user_id, item["planned_date"]):
                skipped += 1  # the person already planned this day themselves
            else:
                plan_repo.insert_imported(
                    conn, user_id, source=SOURCE, external_uid=item["external_uid"], status=STATUS_PLANLAGT, **fields
                )
                added += 1
        removed = plan_repo.delete_vanished_imports(
            conn, user_id, SOURCE, [i["external_uid"] for i in items], timeutil.today().isoformat()
        )
        conn.commit()
    finally:
        conn.close()
    return {"planned_added": added, "planned_updated": updated, "planned_removed": removed, "planned_skipped": skipped}


def _name_runs(user_id: int, completed: list[dict]) -> int:
    named = 0
    conn = get_conn()
    try:
        for run in completed:
            match = activity_repo.find_near_local(conn, user_id, run["start_local"], NAME_WINDOW_SECONDS)
            if match is not None and activity_repo.set_name_if_empty(conn, user_id, match["id"], run["name"]):
                named += 1
        conn.commit()
    finally:
        conn.close()
    return named
