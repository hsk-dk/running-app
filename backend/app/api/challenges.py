from datetime import date

from fastapi import APIRouter, Depends, Response

from app.api.deps import current_user
from app.api.schemas import ChallengeCreate, ChallengeLog, ChallengeOut, ChallengePlan, ChallengeShare
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


@router.put("/{challenge_id}/share", response_model=ChallengeOut)
def share(challenge_id: int, body: ChallengeShare, user: CurrentUser = Depends(current_user)):
    """Show the family a day's number: only a goal you reached or a new best."""
    return challenge_service.share(user.id, challenge_id, body.day)


@router.delete("/{challenge_id}/share", response_model=ChallengeOut)
def unshare(challenge_id: int, day: date | None = None, user: CurrentUser = Depends(current_user)):
    return challenge_service.unshare(user.id, challenge_id, day)
