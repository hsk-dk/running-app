from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import current_user
from app.api.schemas import GarminKeyIn, GarminStatusOut
from app.services import garmin_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/garmin", tags=["garmin"])


@router.get("/status", response_model=GarminStatusOut)
def status(user: CurrentUser = Depends(current_user)):
    return garmin_service.status(user.id)


@router.post("/key", response_model=GarminStatusOut)
def connect(body: GarminKeyIn, background_tasks: BackgroundTasks, user: CurrentUser = Depends(current_user)):
    """Save the person's personal API key (checked against Garmin first) and read the whole history in the background."""
    result = garmin_service.connect(user.id, body.key)
    background_tasks.add_task(garmin_service.after_connect, user.id)
    return result


@router.delete("/connection", response_model=GarminStatusOut)
def disconnect(user: CurrentUser = Depends(current_user)):
    return garmin_service.disconnect(user.id)
