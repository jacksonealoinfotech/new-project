"""Redis client connection manager and health diagnostics."""

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("redis_client")

_redis_client: Redis | None = None


def get_redis_client() -> Redis | None:
    """Retrieve global async Redis client instance if enabled."""
    global _redis_client
    settings = get_settings()
    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        logger.info("redis_client_initialized", url=settings.REDIS_URL)

    return _redis_client


async def check_redis_health() -> bool:
    """Validate Redis connectivity via ping."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        res = await client.ping()
        return bool(res)
    except Exception as err:
        logger.error("redis_health_check_failed", error=str(err))
        return False


async def close_redis_client() -> None:
    """Close Redis client connections on shutdown."""
    global _redis_client
    if _redis_client is not None:
        logger.info("closing_redis_connections")
        await _redis_client.aclose()
        _redis_client = None
