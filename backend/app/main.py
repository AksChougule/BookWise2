import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.utils.logging import (
    clear_request_id,
    clear_trace_id,
    configure_logging,
    get_request_id,
    get_trace_id,
    set_request_id,
    set_trace_id,
)

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = set_request_id(request.headers.get("x-request-id"))
    trace_id = set_trace_id(request.headers.get("x-trace-id"))
    start = perf_counter()
    logger.info(
        "request_started",
        extra={
            "event": "request_started",
            "request_id": request_id,
            "trace_id": trace_id,
            "route": request.url.path,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
        },
    )
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((perf_counter() - start) * 1000)
        logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "request_id": request_id,
                "trace_id": trace_id,
                "route": request.url.path,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error": str(exc),
            },
        )
        clear_request_id()
        clear_trace_id()
        raise

    duration_ms = int((perf_counter() - start) * 1000)
    response.headers["x-request-id"] = request_id
    response.headers["x-trace-id"] = trace_id
    logger.info(
        "request_completed",
        extra={
            "event": "request_completed",
            "request_id": request_id,
            "trace_id": trace_id,
            "route": request.url.path,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    clear_request_id()
    clear_trace_id()
    return response


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "request_id": get_request_id(), "trace_id": get_trace_id()}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_log_configuration() -> None:
    logger.info(
        "startup_configuration",
        extra={
            "event": "startup_configuration",
            "openai_key_present": bool(settings.openai_api_key),
            "youtube_key_present": bool(settings.youtube_api_key),
            "openai_model": settings.openai_model,
            "db_url": settings.database_url,
        },
    )
