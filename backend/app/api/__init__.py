"""HTTP layer: routers only parse requests, call a service and return its result."""
from fastapi import APIRouter

from . import activities, admin, ai, family, garmin, me, planning, runna, smashrun, strava, webhooks

api_router = APIRouter()
for _module in (me, strava, smashrun, runna, garmin, family, activities, planning, ai, admin, webhooks):
    api_router.include_router(_module.router)

__all__ = ["api_router"]
