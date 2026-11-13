from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import RedirectResponse

from app.api.deps import current_user
from app.api.schemas import ConnectOut, StravaStatusOut
from app.config import settings
from app.errors import ForbiddenError
from app.services import strava_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/strava", tags=["strava"])


@router.get("/status", response_model=StravaStatusOut)
def status(user: CurrentUser = Depends(current_user)):
    return strava_service.status(user.id)


@router.post("/connect", response_model=ConnectOut)
def connect(user: CurrentUser = Depends(current_user)):
    """Returns the Strava page the browser should go to. The user comes back through /callback."""
    return strava_service.begin_connect(user.id)


@router.get("/callback")
def callback(
    background_tasks: BackgroundTasks,
    state: str = Query(""),
    code: str | None = Query(None),
    error: str | None = Query(None),
):
    """Strava redirects the browser here. The signed state says which user is connecting."""
    home = settings.APP_BASE_URL.rstrip("/") + "/"
    if error or not code:
        strava_service.read_state(state)  # still reject forged requests
        return RedirectResponse(home + "?strava=denied", status_code=302)
    user_id = strava_service.complete_connect(state, code)
    background_tasks.add_task(strava_service.after_connect, user_id)
    return RedirectResponse(home + "?strava=connected", status_code=302)


@router.delete("/connection", response_model=StravaStatusOut)
def disconnect(user: CurrentUser = Depends(current_user)):
    strava_service.disconnect(user.id)
    return strava_service.status(user.id)
