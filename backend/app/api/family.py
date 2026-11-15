from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import current_user
from app.api.schemas import BonusIn, FamilyActivityDetailOut, FamilyActivityOut, FamilyOut, GoalOut, GoalUpdate, ProfileOut, RewardIn, RewardOut, SplitsOut, StarsOut
from app.services import family_service, star_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/family", tags=["family"])


@router.get("", response_model=FamilyOut)
def family(user: CurrentUser = Depends(current_user)):
    return family_service.list_family(user)


@router.put("/goal", response_model=GoalOut)
def set_goal(payload: GoalUpdate, user: CurrentUser = Depends(current_user)):
    """Declared before /{user_id}/...: 'goal' is not a user id."""
    return family_service.set_goal(user, payload.target_km)


@router.put("/reward", response_model=RewardOut)
def set_reward(payload: RewardIn, user: CurrentUser = Depends(current_user)):
    """A parent sets what the family is saving stars for. Declared before /{user_id}/..."""
    return star_service.set_reward(user, payload.name, payload.cost)


@router.delete("/reward", status_code=204)
def clear_reward(user: CurrentUser = Depends(current_user)):
    star_service.clear_reward(user)
    return Response(status_code=204)


@router.post("/reward/redeem", response_model=RewardOut)
def redeem_reward(user: CurrentUser = Depends(current_user)):
    return star_service.redeem(user)


@router.post("/{user_id}/bonus", response_model=StarsOut)
def give_bonus(user_id: int, payload: BonusIn, user: CurrentUser = Depends(current_user)):
    """A parent gives a bonus star for effort that is not measured."""
    return {**star_service.give_bonus(user, user_id, payload.note), "reward": star_service.reward_progress()}


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
