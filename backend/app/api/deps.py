from fastapi import Depends, Request

from app.errors import ForbiddenError
from app.services import user_service
from app.services.user_service import CurrentUser


def current_user(request: Request) -> CurrentUser:
    """Who is calling. The identity comes from the proxy headers (or the single local user in AUTH_MODE=none)."""
    peer = request.client.host if request.client else None
    return user_service.resolve(peer, request.headers)


def require_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.is_admin:
        raise ForbiddenError("Only administrators can do this")
    return user
