"""Application lifespan manager for graceful resource initialization and teardown."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.observability import setup_telemetry
from app.db.session import check_database_health, dispose_engine, get_engine
from app.infrastructure.http.client import close_http_client, get_http_client
from app.infrastructure.redis.client import close_redis_client, get_redis_client

logger = get_logger("lifecycle")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Execute startup and shutdown procedures cleanly."""
    settings = get_settings()

    # --- STARTUP ---
    configure_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        env=settings.APP_ENV,
        debug=settings.APP_DEBUG,
    )

    setup_telemetry()

    # Initialize and verify database engine
    get_engine()
    db_ok = await check_database_health()
    if not db_ok:
        logger.warning("database_initial_connectivity_check_failed")

    # Initialize Redis if enabled
    if settings.REDIS_ENABLED:
        get_redis_client()

    # Warm up shared HTTP client
    get_http_client()

    logger.info("application_startup_completed")
    yield

    # --- SHUTDOWN ---
    logger.info("application_shutdown_initiated")
    await close_http_client()
    await close_redis_client()
    await dispose_engine()
    logger.info("application_shutdown_completed")
