from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user
from app.api.schemas import FamilyActivityDetailOut, FamilyActivityOut, FamilyOut, GoalOut, GoalUpdate, ProfileOut, SplitsOut
from app.services import family_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/family", tags=["family"])


@router.get("", response_model=FamilyOut)
def family(user: CurrentUser = Depends(current_user)):
    return family_service.list_family(user)


@router.put("/goal", response_model=GoalOut)
def set_goal(payload: GoalUpdate, user: CurrentUser = Depends(current_user)):
    """Declared before /{user_id}/...: 'goal' is not a user id."""
    return family_service.set_goal(user, payload.target_km)


@router.get("/{user_id}/activities", response_model=list[FamilyActivityOut])
def member_activities(user_id: int, limit: int = Query(20, ge=1, le=100), user: CurrentUser = Depends(current_user)):
    return family_service.member_activities(user, user_id, limit=limit)


@router.get("/{user_id}/activities/{activity_id}", response_model=FamilyActivityDetailOut)
def member_activity(user_id: int, activity_id: int, user: CurrentUser = Depends(current_user)):
    return family_service.member_activity(user, user_id, activity_id)


@router.get("/{user_id}/activities/{activity_id}/splits", response_model=SplitsOut)
def member_splits(user_id: int, activity_id: int, user: CurrentUser = Depends(current_user)):
    return family_service.member_splits(user, user_id, activity_id)


@router.get("/{user_id}/activities/{activity_id}/profile", response_model=ProfileOut)
def member_profile(user_id: int, activity_id: int, user: CurrentUser = Depends(current_user)):
    return family_service.member_profile(user, user_id, activity_id)
