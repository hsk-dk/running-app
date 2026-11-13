from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.api.schemas import RunnaLinkIn, RunnaStatusOut
from app.services import planning_service, runna_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/runna", tags=["runna"])


@router.get("/status", response_model=RunnaStatusOut)
def status(user: CurrentUser = Depends(current_user)):
    return runna_service.status(user.id)


@router.post("/link", response_model=RunnaStatusOut)
def connect(body: RunnaLinkIn, user: CurrentUser = Depends(current_user)):
    """Save the person's Runna calendar link and read the plan from it right away."""
    runna_service.connect(user.id, body.url)
    runna_service.sync(user.id)
    planning_service.evaluate_and_sync(user.id)
    return runna_service.status(user.id)


@router.post("/sync")
def sync(user: CurrentUser = Depends(current_user)):
    result = runna_service.sync(user.id)
    planning_service.evaluate_and_sync(user.id)
    return result


@router.delete("/link", response_model=RunnaStatusOut)
def disconnect(user: CurrentUser = Depends(current_user)):
    return runna_service.disconnect(user.id)
