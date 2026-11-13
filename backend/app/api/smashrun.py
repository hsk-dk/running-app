from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import RedirectResponse

from app.api.deps import current_user
from app.api.schemas import ConnectOut, SmashrunStatusOut
from app.config import settings
from app.services import smashrun_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/smashrun", tags=["smashrun"])


@router.get("/status", response_model=SmashrunStatusOut)
def status(user: CurrentUser = Depends(current_user)):
    return smashrun_service.status(user.id)


@router.post("/connect", response_model=ConnectOut)
def connect(user: CurrentUser = Depends(current_user)):
    """Returns the Smashrun page the browser should go to. The user comes back through /callback."""
    return smashrun_service.begin_connect(user.id)


@router.get("/callback")
def callback(
    background_tasks: BackgroundTasks,
    state: str = Query(""),
    code: str | None = Query(None),
    error: str | None = Query(None),
):
    home = settings.APP_BASE_URL.rstrip("/") + "/"
    if error or not code:
        smashrun_service.read_state(state)  # still reject forged requests
        return RedirectResponse(home + "?smashrun=denied", status_code=302)
    user_id = smashrun_service.complete_connect(state, code)
    background_tasks.add_task(smashrun_service.after_connect, user_id)
    return RedirectResponse(home + "?smashrun=connected", status_code=302)


@router.delete("/connection", response_model=SmashrunStatusOut)
def disconnect(user: CurrentUser = Depends(current_user)):
    return smashrun_service.disconnect(user.id)
