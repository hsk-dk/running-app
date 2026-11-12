import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import NotFoundError

logger = logging.getLogger(__name__)


def _format_validation_errors(errors: list[dict]) -> str:
    parts = []
    for err in errors:
        loc = ".".join(str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path"))
        msg = err.get("msg", "invalid")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc) or "Not found"})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errors = jsonable_encoder(exc.errors())
        # `detail` is a readable string because the frontend prints it verbatim.
        return JSONResponse(
            status_code=422,
            content={"detail": _format_validation_errors(errors), "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
