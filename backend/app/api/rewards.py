from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.api.schemas import BadgesOut, StarsOut
from app.services import badge_service, star_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api", tags=["rewards"])


@router.get("/stars", response_model=StarsOut)
def stars(user: CurrentUser = Depends(current_user)):
    """Your own stars this week and in all, and the family's reward with everyone's stars together."""
    return {**star_service.mine(user.id), "reward": star_service.reward_progress()}


@router.get("/badges", response_model=BadgesOut)
def badges(user: CurrentUser = Depends(current_user)):
    return badge_service.for_user(user.id)
