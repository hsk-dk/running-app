from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user
from app.api.schemas import ActivityDetailOut, ActivityOut, MonthlyVolumeOut, SplitsOut
from app.services import reporting_service, splits_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api", tags=["activities"])


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(limit: int = Query(100, ge=1, le=500), user: CurrentUser = Depends(current_user)):
    return reporting_service.list_activities(user.id, limit=limit)


@router.get("/activities/{activity_id}", response_model=ActivityDetailOut)
def get_activity(activity_id: int, user: CurrentUser = Depends(current_user)):
    return reporting_service.get_activity(user.id, activity_id)


@router.get("/activities/{activity_id}/splits", response_model=SplitsOut)
def get_splits(activity_id: int, user: CurrentUser = Depends(current_user)):
    return splits_service.get_splits(user.id, activity_id)


@router.get("/metrics/summary")
def summary(user: CurrentUser = Depends(current_user)):
    return reporting_service.summary(user.id)


@router.get("/metrics/monthly-volume", response_model=list[MonthlyVolumeOut])
def monthly_volume(user: CurrentUser = Depends(current_user)):
    return reporting_service.monthly_volume(user.id)
