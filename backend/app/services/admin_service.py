from app.db import get_conn
from app.errors import NotConnectedError, UpstreamError
from app.repositories import activities as activity_repo
from app.repositories import smashrun_accounts, strava_accounts, sync_state, user_state, webhook_events
from app.services import planning_service, smashrun_service
from app.services.sync_service import ingest_recent, set_state


def get_status(user_id: int, is_admin: bool = False):
    """The user's own sync state. Admins also see the totals for all users."""
    conn = get_conn()
    try:
        scope = None if is_admin else user_id
        return {
            "last_sync_at": user_state.get(conn, user_id, "last_sync_at"),
            "last_webhook_at": user_state.get(conn, user_id, "last_webhook_at") or (sync_state.get(conn, "last_webhook_at") if is_admin else None),
            "last_ingest_result": user_state.get(conn, user_id, "last_ingest_result"),
            "last_error": user_state.get(conn, user_id, "last_error"),
            "webhook_event_count": webhook_events.count(conn, scope),
            "last_webhook": webhook_events.latest(conn, scope),
            "strava_connected": strava_accounts.get(conn, user_id) is not None,
        }
    finally:
        conn.close()


def run_ingest(user_id: int, pages: int = 3):
    """Sync every source the user has connected. One failing source does not stop the others."""
    conn = get_conn()
    try:
        sources = []
        if smashrun_accounts.get(conn, user_id) is not None:
            sources.append("smashrun")
        if strava_accounts.get(conn, user_id) is not None:
            sources.append("strava")
    finally:
        conn.close()
    if not sources:
        sources = ["strava"]  # raises 'not connected' with a clear message

    results: dict = {}
    errors: dict = {}
    failures: list[Exception] = []
    for source in sources:
        try:
            results[source] = smashrun_service.ingest_recent(user_id) if source == "smashrun" else ingest_recent(user_id, pages=pages)
        except Exception as exc:
            errors[source] = str(exc)
            failures.append(exc)
    if errors:
        set_state(user_id, "last_error", "; ".join(f"{name}: {message}" for name, message in errors.items()))
    if not results:
        if len(failures) == 1 and isinstance(failures[0], NotConnectedError):
            raise failures[0]  # 'not connected' is a 409 with its own message
        raise UpstreamError("; ".join(f"{name}: {message}" for name, message in errors.items()))
    if "strava" in results and len(results) == 1 and not errors:
        return results["strava"]  # unchanged answer for Strava-only users
    return {**results, **({"errors": errors} if errors else {})}


def recalculate_plan(user_id: int):
    return planning_service.evaluate_and_sync(user_id)


def rebuild_links(user_id: int):
    return planning_service.rebuild_activity_links(user_id)


def get_health(user_id: int, is_admin: bool = False):
    """Do activities and plans point at each other? Admins check every user at once."""
    conn = get_conn()
    try:
        mismatch = activity_repo.count_link_mismatches(conn, None if is_admin else user_id)
    finally:
        conn.close()
    return {"ok": mismatch == 0, "mismatch_count": mismatch}
