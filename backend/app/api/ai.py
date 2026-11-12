from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.services import ai_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/suggestions")
def suggestions(user: CurrentUser = Depends(current_user)):
    return ai_service.generate_suggestions(user.id)
