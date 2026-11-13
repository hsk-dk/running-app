from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.api.schemas import (
    DeletedOut,
    MatchActivityRequest,
    PlannedRunCreate,
    PlannedRunOut,
    PlannedRunUpdate,
    WeeklyConsistencyOut,
)
from app.services import planning_service, reporting_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/planning", tags=["planning"])


@router.get("", response_model=list[PlannedRunOut])
def list_planned_runs(user: CurrentUser = Depends(current_user)):
    return planning_service.list_planned_runs(user.id)


@router.get("/weekly-consistency", response_model=list[WeeklyConsistencyOut])
def weekly_consistency(user: CurrentUser = Depends(current_user)):
    return reporting_service.weekly_consistency(user.id, tolerance_days=1)


@router.post("", response_model=PlannedRunOut)
def add_planned_run(payload: PlannedRunCreate, user: CurrentUser = Depends(current_user)):
    return planning_service.add_planned_run(user.id, payload.model_dump())


@router.post("/evaluate")
def evaluate(user: CurrentUser = Depends(current_user)):
    return planning_service.evaluate_and_sync(user.id)


@router.post("/{planned_run_id}/mark-skipped")
def mark_skipped(planned_run_id: int, user: CurrentUser = Depends(current_user)):
    return planning_service.mark_planned_run_skipped(user.id, planned_run_id)


@router.post("/{planned_run_id}/mark-rescheduled")
def mark_rescheduled(planned_run_id: int, user: CurrentUser = Depends(current_user)):
    return planning_service.mark_planned_run_rescheduled(user.id, planned_run_id)


@router.post("/{planned_run_id}/clear-match")
def clear_match(planned_run_id: int, user: CurrentUser = Depends(current_user)):
    return planning_service.clear_planned_run_match(user.id, planned_run_id)


@router.post("/{planned_run_id}/match-activity")
def match_activity(planned_run_id: int, payload: MatchActivityRequest, user: CurrentUser = Depends(current_user)):
    return planning_service.match_activity_to_planned_run(user.id, planned_run_id, payload.activity_id)


@router.put("/{planned_run_id}")
def update_planned_run(planned_run_id: int, payload: PlannedRunUpdate, user: CurrentUser = Depends(current_user)):
    return planning_service.update_planned_run(user.id, planned_run_id, payload.model_dump())


@router.delete("/{planned_run_id}", response_model=DeletedOut)
def delete_planned_run(planned_run_id: int, user: CurrentUser = Depends(current_user)):
    return planning_service.delete_planned_run(user.id, planned_run_id)
