from fastapi import APIRouter

from app.api.schemas import (
    DeletedOut,
    MatchActivityRequest,
    PlannedRunCreate,
    PlannedRunOut,
    PlannedRunUpdate,
    WeeklyConsistencyOut,
)
from app.services import planning_service, reporting_service

router = APIRouter(prefix="/api/planning", tags=["planning"])


@router.get("", response_model=list[PlannedRunOut])
def list_planned_runs():
    return planning_service.list_planned_runs()


@router.get("/weekly-consistency", response_model=list[WeeklyConsistencyOut])
def weekly_consistency():
    return reporting_service.weekly_consistency(tolerance_days=1)


@router.post("", response_model=PlannedRunOut)
def add_planned_run(payload: PlannedRunCreate):
    return planning_service.add_planned_run(payload.model_dump())


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
def match_activity(planned_run_id: int, payload: MatchActivityRequest):
    return planning_service.match_activity_to_planned_run(planned_run_id, payload.activity_id)


@router.put("/{planned_run_id}")
def update_planned_run(planned_run_id: int, payload: PlannedRunUpdate):
    return planning_service.update_planned_run(planned_run_id, payload.model_dump())


@router.delete("/{planned_run_id}", response_model=DeletedOut)
def delete_planned_run(planned_run_id: int):
    return planning_service.delete_planned_run(planned_run_id)
