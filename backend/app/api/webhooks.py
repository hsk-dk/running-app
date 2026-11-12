from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.api.schemas import StravaWebhookEvent
from app.services import webhook_service

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("/strava")
def verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    result = webhook_service.verify_subscription(hub_mode, hub_verify_token, hub_challenge)
    if result is None:
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return result


@router.post("/strava")
def receive(event: StravaWebhookEvent, background_tasks: BackgroundTasks):
    payload = event.model_dump(exclude_unset=True)
    result = webhook_service.receive_event(payload)
    if result["needs_processing"]:
        background_tasks.add_task(webhook_service.process_stored_event, result["event_id"], payload)
    return {"stored": result["stored"], "duplicate": result["duplicate"]}
