from fastapi import APIRouter, Query

from app.api.schemas import HealthOut
from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/status")
def status():
    return admin_service.get_status()


@router.post("/ingest")
def ingest(pages: int = Query(3, ge=1, le=20)):
    return admin_service.run_ingest(pages=pages)


@router.post("/recalculate-plan")
def recalculate_plan():
    return admin_service.recalculate_plan()


@router.post("/rebuild-links")
def rebuild_links():
    return admin_service.rebuild_links()


@router.get("/health", response_model=HealthOut)
def health():
    return admin_service.get_health()
