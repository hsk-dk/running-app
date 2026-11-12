from app.db import get_conn
from app.repositories import sync_state, webhook_events


def set_state(key: str, value: str) -> None:
    conn = get_conn()
    try:
        sync_state.upsert(conn, key, value)
        conn.commit()
    finally:
        conn.close()


def get_state(key: str):
    conn = get_conn()
    try:
        return sync_state.get(conn, key)
    finally:
        conn.close()


def clear_last_error() -> None:
    set_state("last_error", "")


def get_admin_status():
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
