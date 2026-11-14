from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user
from app.api.schemas import ChildUpdate, HealthOut, PersonOut
from app.services import admin_service, user_service
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


@router.get("/users", response_model=list[PersonOut])
def users(user: CurrentUser = Depends(current_user)):
    return user_service.list_people(user)


@router.put("/users/{user_id}/child", response_model=PersonOut)
def set_child(user_id: int, payload: ChildUpdate, user: CurrentUser = Depends(current_user)):
    target = user_service.set_child(user, user_id, payload.is_child)
    return {"id": target.id, "name": target.display_name, "username": target.username, "role": target.role, "is_child": target.is_child}
