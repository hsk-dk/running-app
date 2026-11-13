from app.db import get_conn
from app.errors import NotConnectedError, UpstreamError
from app.repositories import activities as activity_repo
from app.repositories import calendar_feeds, garmin_accounts, smashrun_accounts, user_state
from app.services import garmin_service, planning_service, runna_service, smashrun_service


def get_status(user_id: int, is_admin: bool = False):
    """The user's own sync state."""
    conn = get_conn()
    try:
        return {
            "last_sync_at": user_state.get(conn, user_id, "last_sync_at"),
            "last_ingest_result": user_state.get(conn, user_id, "last_ingest_result"),
            "last_error": user_state.get(conn, user_id, "last_error"),
        }
    finally:
        conn.close()


def _set_error(user_id: int, message: str) -> None:
    conn = get_conn()
    try:
        user_state.upsert(conn, user_id, "last_error", message)
        conn.commit()
    finally:
        conn.close()


def run_ingest(user_id: int, pages: int = 3):  # `pages` is kept for the API; every source pages on its own
    """Sync every source the user has connected. One failing source does not stop the others."""
    conn = get_conn()
    try:
        sources = []
        if garmin_accounts.get(conn, user_id) is not None:
            sources.append("garmin")
        if smashrun_accounts.get(conn, user_id) is not None:
            sources.append("smashrun")
        if calendar_feeds.get(conn, user_id) is not None:
            sources.append("runna")  # last: it names the runs the other sources just brought in
    finally:
        conn.close()
    if not sources:
        raise NotConnectedError("Ingen datakilde er forbundet. Forbind Garmin under Mere → Mig.")

    results: dict = {}
    errors: dict = {}
    failures: list[Exception] = []
    for source in sources:
        try:
            if source == "garmin":
                results[source] = garmin_service.ingest_recent(user_id)
            elif source == "smashrun":
                results[source] = smashrun_service.ingest_recent(user_id)
            else:
                results[source] = runna_service.sync(user_id)
        except Exception as exc:
            errors[source] = str(exc)
            failures.append(exc)
    if errors:
        _set_error(user_id, "; ".join(f"{name}: {message}" for name, message in errors.items()))
    if not results:
        if len(failures) == 1 and isinstance(failures[0], NotConnectedError):
            raise failures[0]  # 'not connected' is a 409 with its own message
        raise UpstreamError("; ".join(f"{name}: {message}" for name, message in errors.items()))
    if results:
        planning_service.evaluate_and_sync(user_id)  # new runs and a changed plan must be matched up again
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
