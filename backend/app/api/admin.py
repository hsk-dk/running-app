from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user
from app.api.schemas import HealthOut
from app.services import admin_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/status")
def status(user: CurrentUser = Depends(current_user)):
    return admin_service.get_status(user.id, user.is_admin)


@router.post("/ingest")
def ingest(pages: int = Query(3, ge=1, le=20), user: CurrentUser = Depends(current_user)):
    return admin_service.run_ingest(user.id, pages=pages)


@router.post("/recalculate-plan")
def recalculate_plan(user: CurrentUser = Depends(current_user)):
    return admin_service.recalculate_plan(user.id)


@router.post("/rebuild-links")
def rebuild_links(user: CurrentUser = Depends(current_user)):
    return admin_service.rebuild_links(user.id)


@router.get("/health", response_model=HealthOut)
def health(user: CurrentUser = Depends(current_user)):
    return admin_service.get_health(user.id, user.is_admin)
