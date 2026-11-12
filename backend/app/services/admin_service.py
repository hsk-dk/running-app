from app.db import get_conn
from app.repositories import activities as activity_repo
from app.repositories import sync_state, webhook_events
from app.services import planning_service
from app.services.sync_service import ingest_recent, set_state


def get_status():
    conn = get_conn()
    try:
        return {
            "last_sync_at": sync_state.get(conn, "last_sync_at"),
            "last_webhook_at": sync_state.get(conn, "last_webhook_at"),
            "last_ingest_result": sync_state.get(conn, "last_ingest_result"),
            "last_error": sync_state.get(conn, "last_error"),
            "webhook_event_count": webhook_events.count(conn),
            "last_webhook": webhook_events.latest(conn),
        }
    finally:
        conn.close()


def run_ingest(pages: int = 3):
    try:
        return ingest_recent(pages=pages)
    except Exception as exc:
        set_state("last_error", str(exc))
        raise


def recalculate_plan():
    return planning_service.evaluate_and_sync()


def rebuild_links():
    return planning_service.rebuild_activity_links()


def get_health():
    conn = get_conn()
    try:
        mismatch = activity_repo.count_link_mismatches(conn)
    finally:
        conn.close()
    return {"ok": mismatch == 0, "mismatch_count": mismatch}
