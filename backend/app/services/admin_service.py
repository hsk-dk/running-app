from app.admin_status import get_admin_status, set_state
from app.db import get_conn
from app.ingest import ingest_recent
from app.repositories import activities as activity_repo
from app.services import planning_service


def get_status():
    return get_admin_status()


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
