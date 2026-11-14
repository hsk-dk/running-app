"""HTTP layer: routers only parse requests, call a service and return its result."""
from fastapi import APIRouter

from . import activities, admin, ai, challenges, family, garmin, me, planning, runna, smashrun

api_router = APIRouter()
for _module in (me, smashrun, runna, garmin, challenges, family, activities, planning, ai, admin):
    api_router.include_router(_module.router)

__all__ = ["api_router"]
