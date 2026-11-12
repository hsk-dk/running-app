from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.errors import register_exception_handlers
from app.config import settings
from app.db import init_db
from app.services import planning_service

# TODO(#15): move startup work into a FastAPI lifespan handler.
init_db()
planning_service.rebuild_activity_links()

app = FastAPI(title="Running")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


register_exception_handlers(app)
app.include_router(api_router)
