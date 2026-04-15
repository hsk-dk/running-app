from app.db import get_conn


def set_state(key: str, value: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO sync_state (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def get_state(key: str):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value, updated_at FROM sync_state WHERE key = ?",
            (key,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def clear_last_error() -> None:
    set_state("last_error", "")


def get_admin_status():
    conn = get_conn()
    try:
        webhook_count = conn.execute(
            "SELECT COUNT(*) AS c FROM webhook_events"
        ).fetchone()["c"]

        last_webhook = conn.execute(
            "SELECT created_at, object_type, aspect_type FROM webhook_events ORDER BY id DESC LIMIT 1"
        ).fetchone()

        result = {
            "last_sync_at": get_state("last_sync_at"),
            "last_webhook_at": get_state("last_webhook_at"),
            "last_ingest_result": get_state("last_ingest_result"),
            "last_error": get_state("last_error"),
            "webhook_event_count": webhook_count,
            "last_webhook": dict(last_webhook) if last_webhook else None,
        }
        return result
    finally:
        conn.close()
