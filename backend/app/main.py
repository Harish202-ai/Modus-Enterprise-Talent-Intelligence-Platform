import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import cache, database
from app.payments import PaymentsUnavailable
from app.api import admin_content, admin_scores, admin_users, assessments, attempts, auth, candidates, commerce, health, interview, profile, progress, reports, roadmap, scores, site, support
from app.config import get_settings
from app.logging_config import configure_logging
from app.services.auth import AuthError
from app.services.content import ContentError

settings = get_settings()
configure_logging(settings.log_level)
log = logging.getLogger("meti.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("starting", extra={"environment": settings.environment, "mongo_db": settings.mongo_db})
    try:
        await database.ensure_indexes()
    except Exception:  # noqa: BLE001 - keep serving so /health can report the outage
        log.exception("index bootstrap failed at startup")
    yield
    await cache.close_redis()
    database.close_client()
    log.info("stopped")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_log(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error", extra={"request_id": request_id, "path": request.url.path})
        raise
    response.headers["X-Request-ID"] = request_id
    log.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        },
    )
    return response


@app.exception_handler(ContentError)
async def content_error(_: Request, exc: ContentError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "errors": exc.errors})


@app.exception_handler(AuthError)
async def auth_error(_: Request, exc: AuthError) -> JSONResponse:
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message}, headers=headers)


@app.exception_handler(PaymentsUnavailable)
async def payments_unavailable(_: Request, exc: PaymentsUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(health.router)
app.include_router(site.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(candidates.router, prefix=settings.api_prefix)
app.include_router(commerce.router, prefix=settings.api_prefix)
app.include_router(attempts.router, prefix=settings.api_prefix)
app.include_router(profile.router, prefix=settings.api_prefix)
app.include_router(admin_content.router, prefix=settings.api_prefix)
app.include_router(assessments.router, prefix=settings.api_prefix)
app.include_router(scores.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(roadmap.router, prefix=settings.api_prefix)
app.include_router(support.router, prefix=settings.api_prefix)
app.include_router(admin_scores.router, prefix=settings.api_prefix)
app.include_router(progress.router, prefix=settings.api_prefix)
app.include_router(admin_users.router, prefix=settings.api_prefix)
app.include_router(interview.router, prefix=settings.api_prefix)
