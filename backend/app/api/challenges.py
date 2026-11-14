from fastapi import APIRouter, Depends, Response

from app.api.deps import current_user
from app.api.schemas import ChallengeCreate, ChallengeLog, ChallengeOut, ChallengePlan
from app.services import challenge_service
from app.services.user_service import CurrentUser

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.get("", response_model=list[ChallengeOut])
def list_challenges(user: CurrentUser = Depends(current_user)):
    return challenge_service.list_for(user.id)


@router.post("", response_model=ChallengeOut, status_code=201)
def create_challenge(body: ChallengeCreate, user: CurrentUser = Depends(current_user)):
    return challenge_service.create(user.id, body.model_dump())


@router.put("/{challenge_id}", response_model=ChallengeOut)
def update_challenge(challenge_id: int, body: ChallengePlan, user: CurrentUser = Depends(current_user)):
    return challenge_service.update(user.id, challenge_id, body.model_dump())


@router.delete("/{challenge_id}", status_code=204)
def delete_challenge(challenge_id: int, user: CurrentUser = Depends(current_user)):
    challenge_service.archive(user.id, challenge_id)
    return Response(status_code=204)


@router.put("/{challenge_id}/log", response_model=ChallengeOut)
def log_count(challenge_id: int, body: ChallengeLog, user: CurrentUser = Depends(current_user)):
    """Write how many you did on a day (today when left out). 0 clears the day."""
    return challenge_service.log(user.id, challenge_id, body.count, body.day)
