from fastapi import APIRouter, HTTPException, Request

from app.services import planning_service, reporting_service

router = APIRouter(prefix="/api/planning", tags=["planning"])


@router.get("")
def list_planned_runs():
    return planning_service.list_planned_runs()


@router.get("/weekly-consistency")
def weekly_consistency():
    return reporting_service.weekly_consistency(tolerance_days=1)


@router.post("")
def add_planned_run(payload: dict):
    return planning_service.add_planned_run(payload)


@router.post("/evaluate")
def evaluate():
    return planning_service.evaluate_and_sync()


@router.post("/{planned_run_id}/mark-skipped")
def mark_skipped(planned_run_id: int):
    return planning_service.mark_planned_run_skipped(planned_run_id)


@router.post("/{planned_run_id}/mark-rescheduled")
def mark_rescheduled(planned_run_id: int):
    return planning_service.mark_planned_run_rescheduled(planned_run_id)


@router.post("/{planned_run_id}/clear-match")
def clear_match(planned_run_id: int):
    return planning_service.clear_planned_run_match(planned_run_id)


@router.post("/{planned_run_id}/match-activity")
async def match_activity(planned_run_id: int, request: Request):
    payload = await request.json()
    activity_id = payload.get("activity_id")
    if not activity_id:
        raise HTTPException(status_code=400, detail="activity_id is required")
    return planning_service.match_activity_to_planned_run(planned_run_id, int(activity_id))


@router.put("/{planned_run_id}")
async def update_planned_run(planned_run_id: int, request: Request):
    payload = await request.json()
    return planning_service.update_planned_run(planned_run_id, payload)


@router.delete("/{planned_run_id}")
def delete_planned_run(planned_run_id: int):
    return planning_service.delete_planned_run(planned_run_id)
