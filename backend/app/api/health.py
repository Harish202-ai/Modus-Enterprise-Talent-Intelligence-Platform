from fastapi import APIRouter, Response

from app import cache, database
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(response: Response) -> dict:
    """Liveness + dependency check. 200 when Mongo and Redis answer, 503 otherwise."""
    checks = {"mongo": await database.ping(), "redis": await cache.ping()}
    ok = all(checks.values())
    if not ok:
        response.status_code = 503
    settings = get_settings()
    return {
        "status": "ok" if ok else "degraded",
        "service": settings.app_name,
        "environment": settings.environment,
        "checks": {name: "up" if up else "down" for name, up in checks.items()},
    }
