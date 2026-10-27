"""Operational readiness and liveness health probe endpoints."""

from typing import Any

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.db.session import check_database_health

router = APIRouter(prefix="/health", tags=["Health & Readiness"])


@router.get(
    "/liveness",
    status_code=status.HTTP_200_OK,
    summary="Application liveness probe",
)
async def liveness_probe() -> dict[str, str]:
    """Lightweight check verifying that the application process is running and accepting traffic."""
    return {"status": "ok"}


@router.get(
    "/readiness",
    summary="Application readiness probe",
)
async def readiness_probe(response: Response) -> dict[str, Any]:
    """Readiness check validating connectivity to required backing dependencies (database, Redis)."""
    settings = get_settings()
    db_healthy = await check_database_health()

    checks: dict[str, str] = {
        "database": "healthy" if db_healthy else "unhealthy",
    }

    is_ready = db_healthy

    # Optional Redis check if enabled
    if settings.REDIS_ENABLED:
        from app.infrastructure.redis.client import check_redis_health

        redis_healthy = await check_redis_health()
        checks["redis"] = "healthy" if redis_healthy else "unhealthy"
        if not redis_healthy:
            is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "checks": checks,
        }

    response.status_code = status.HTTP_200_OK
    return {
        "status": "ready",
        "checks": checks,
    }
