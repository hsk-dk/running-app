from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user
from app.api.schemas import ActivityDetailOut, ActivityOut, IndoorOut, MonthlyVolumeOut, OtherOut, ProfileOut, RouteOut, RunProfileOut, SplitsOut
from app.services import garmin_service, reporting_service, splits_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api", tags=["activities"])


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(limit: int = Query(100, ge=1, le=500), user: CurrentUser = Depends(current_user)):
    return reporting_service.list_activities(user.id, limit=limit)


@router.get("/activities/routes", response_model=list[RouteOut])
def routes(limit: int = Query(400, ge=1, le=1000), user: CurrentUser = Depends(current_user)):
    """Declared before /activities/{activity_id}, which would otherwise try to read 'routes' as an id."""
    return reporting_service.routes(user.id, limit=limit)


@router.get("/activities/indoor", response_model=list[IndoorOut])
def indoor(limit: int = Query(2000, ge=1, le=5000), user: CurrentUser = Depends(current_user)):
    """Runs without a GPS route. Declared before /activities/{activity_id}."""
    return reporting_service.indoor(user.id, limit=limit)


@router.get("/activities/other", response_model=list[OtherOut])
def other(limit: int = Query(3000, ge=1, le=10000), user: CurrentUser = Depends(current_user)):
    """Walks, rides, rowing and the rest: not runs. Declared before /activities/{activity_id}."""
    return reporting_service.other(user.id, limit=limit)


@router.get("/activities/profiles", response_model=list[RunProfileOut])
def profiles(limit: int = Query(16, ge=1, le=60), user: CurrentUser = Depends(current_user)):
    """Declared before /activities/{activity_id}. Only the signed-in person's own runs (heart rate included)."""
    return reporting_service.profiles(user.id, limit=limit)


@router.get("/activities/{activity_id}", response_model=ActivityDetailOut)
def get_activity(activity_id: int, user: CurrentUser = Depends(current_user)):
    return reporting_service.get_activity(user.id, activity_id)


@router.get("/activities/{activity_id}/splits", response_model=SplitsOut)
def get_splits(activity_id: int, user: CurrentUser = Depends(current_user)):
    return splits_service.get_splits(user.id, activity_id)


@router.get("/activities/{activity_id}/profile", response_model=ProfileOut)
def get_profile(activity_id: int, user: CurrentUser = Depends(current_user)):
    return garmin_service.get_profile(user.id, activity_id)


@router.get("/metrics/summary")
def summary(user: CurrentUser = Depends(current_user)):
    return reporting_service.summary(user.id)


@router.get("/metrics/monthly-volume", response_model=list[MonthlyVolumeOut])
def monthly_volume(user: CurrentUser = Depends(current_user)):
    return reporting_service.monthly_volume(user.id)
