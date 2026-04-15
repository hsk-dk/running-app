from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db, get_conn
from app.ingest import ingest_recent
from app.metrics import rebuild_metrics, get_summary, get_monthly_volume, get_activities
from app.planning import (
    list_planned_runs,
    add_planned_run,
    mark_planned_run_skipped,
    mark_planned_run_rescheduled,
    clear_planned_run_match,
    match_activity_to_planned_run,
    update_planned_run,
    delete_planned_run,
    rebuild_activity_links,
    evaluate_and_sync,
)
from app.matching import get_weekly_consistency
from app.webhooks import verify_subscription, process_event
from app.admin_status import get_admin_status, set_state

init_db()
rebuild_activity_links()

app = FastAPI(title="Running")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/activities")
def api_activities(limit: int = 100):
    return get_activities(limit=limit)


@app.get("/api/metrics/summary")
def api_summary():
    return get_summary()


@app.get("/api/metrics/monthly-volume")
def api_monthly_volume():
    return get_monthly_volume()


@app.get("/api/planning")
def api_planning():
    return list_planned_runs()


@app.get("/api/planning/weekly-consistency")
def api_weekly_consistency():
    return get_weekly_consistency(tolerance_days=1)


@app.post("/api/planning")
def api_add_planned_run(payload: dict):
    return add_planned_run(payload)


@app.post("/api/planning/evaluate")
def api_evaluate_planning():
    return evaluate_and_sync()


@app.post("/api/planning/{planned_run_id}/mark-skipped")
def api_mark_skipped(planned_run_id: int):
    return mark_planned_run_skipped(planned_run_id)


@app.post("/api/planning/{planned_run_id}/mark-rescheduled")
def api_mark_rescheduled(planned_run_id: int):
    return mark_planned_run_rescheduled(planned_run_id)


@app.post("/api/planning/{planned_run_id}/clear-match")
def api_clear_match(planned_run_id: int):
    return clear_planned_run_match(planned_run_id)


@app.post("/api/planning/{planned_run_id}/match-activity")
async def api_match_activity(planned_run_id: int, request: Request):
    payload = await request.json()
    activity_id = payload.get("activity_id")
    if not activity_id:
        raise HTTPException(status_code=400, detail="activity_id is required")
    return match_activity_to_planned_run(planned_run_id, int(activity_id))


@app.put("/api/planning/{planned_run_id}")
async def api_update_planned_run(planned_run_id: int, request: Request):
    payload = await request.json()
    return update_planned_run(planned_run_id, payload)


@app.delete("/api/planning/{planned_run_id}")
def api_delete_planned_run(planned_run_id: int):
    return delete_planned_run(planned_run_id)


@app.get("/api/admin/status")
def api_admin_status():
    return get_admin_status()


@app.post("/api/admin/ingest")
def api_ingest(pages: int = 3):
    try:
        return ingest_recent(pages=pages)
    except Exception as exc:
        set_state("last_error", str(exc))
        raise


@app.post("/api/admin/rebuild-metrics")
def api_rebuild_metrics():
    return rebuild_metrics()


@app.post("/api/admin/recalculate-plan")
def api_recalculate_plan():
    return evaluate_and_sync()


@app.post("/api/admin/rebuild-links")
def api_rebuild_links():
    return rebuild_activity_links()


@app.get("/api/admin/health")
def api_health():
    conn = get_conn()
    try:
        mismatch = conn.execute(
            """
            SELECT COUNT(*)
            FROM activities a
            WHERE
                (a.matched_planned_run_id IS NULL AND EXISTS (
                    SELECT 1 FROM planned_runs p WHERE p.matched_activity_id = a.id
                ))
                OR
                (a.matched_planned_run_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM planned_runs p WHERE p.id = a.matched_planned_run_id
                ))
            """
        ).fetchone()[0]

        return {
            "ok": mismatch == 0,
            "mismatch_count": mismatch,
        }
    finally:
        conn.close()


@app.get("/api/webhooks/strava")
def strava_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    result = verify_subscription(hub_mode, hub_verify_token, hub_challenge)
    if result is None:
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return result


@app.post("/api/webhooks/strava")
async def strava_webhook_event(request: Request):
    payload = await request.json()
    return process_event(payload)
