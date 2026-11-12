from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user
from app.api.schemas import ActivityDetailOut, ActivityOut, FamilyOut
from app.services import family_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/family", tags=["family"])


@router.get("", response_model=FamilyOut)
def family(user: CurrentUser = Depends(current_user)):
    return family_service.list_family(user)


@router.get("/{user_id}/activities", response_model=list[ActivityOut])
def member_activities(user_id: int, limit: int = Query(20, ge=1, le=100), user: CurrentUser = Depends(current_user)):
    return family_service.member_activities(user, user_id, limit=limit)


@router.get("/{user_id}/activities/{activity_id}", response_model=ActivityDetailOut)
def member_activity(user_id: int, activity_id: int, user: CurrentUser = Depends(current_user)):
    return family_service.member_activity(user, user_id, activity_id)
