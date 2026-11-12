from fastapi import APIRouter, Query

from app.api.schemas import ActivityDetailOut, ActivityOut, MonthlyVolumeOut
from app.services import reporting_service

router = APIRouter(prefix="/api", tags=["activities"])


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(limit: int = Query(100, ge=1, le=500)):
    return reporting_service.list_activities(limit=limit)


@router.get("/activities/{activity_id}", response_model=ActivityDetailOut)
def get_activity(activity_id: int):
    return reporting_service.get_activity(activity_id)


@router.get("/metrics/summary")
def summary():
    return reporting_service.summary()


@router.get("/metrics/monthly-volume", response_model=list[MonthlyVolumeOut])
def monthly_volume():
    return reporting_service.monthly_volume()
