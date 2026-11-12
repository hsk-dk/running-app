from fastapi import APIRouter

from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/status")
def status():
    return admin_service.get_status()


@router.post("/ingest")
def ingest(pages: int = 3):
    return admin_service.run_ingest(pages=pages)


@router.post("/rebuild-metrics")
def rebuild_metrics():
    return admin_service.run_rebuild_metrics()


@router.post("/recalculate-plan")
def recalculate_plan():
    return admin_service.recalculate_plan()


@router.post("/rebuild-links")
def rebuild_links():
    return admin_service.rebuild_links()


@router.get("/health")
def health():
    return admin_service.get_health()
