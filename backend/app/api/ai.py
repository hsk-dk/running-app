from fastapi import APIRouter

from app.services import ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/suggestions")
def suggestions():
    return ai_service.generate_suggestions()
