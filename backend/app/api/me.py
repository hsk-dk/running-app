from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.api.schemas import MeOut, MeUpdate
from app.services import user_service
from app.services.user_service import CurrentUser
from app.config import settings
from app.services import smashrun_service, strava_service

router = APIRouter(prefix="/api", tags=["me"])


def _me(user: CurrentUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "sharing_level": user.sharing_level,
        "family_sharing_enabled": settings.FAMILY_SHARING_ENABLED,
        "strava": strava_service.status(user.id),
        "smashrun": smashrun_service.status(user.id),
    }


@router.get("/me", response_model=MeOut)
def get_me(user: CurrentUser = Depends(current_user)):
    return _me(user)


@router.put("/me", response_model=MeOut)
def update_me(payload: MeUpdate, user: CurrentUser = Depends(current_user)):
    return _me(user_service.update_profile(user.id, payload.sharing_level, payload.display_name))
