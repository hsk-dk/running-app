from fastapi import APIRouter

from app.services import reporting_service

router = APIRouter(prefix="/api", tags=["activities"])


@router.get("/activities")
def list_activities(limit: int = 100):
    return reporting_service.list_activities(limit=limit)


@router.get("/metrics/summary")
def summary():
    return reporting_service.summary()


@router.get("/metrics/monthly-volume")
def monthly_volume():
    return reporting_service.monthly_volume()
