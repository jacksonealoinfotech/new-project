"""Cache-aside service supporting in-memory and Redis backends."""

import json
import time
from typing import Any, Protocol

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.redis.client import get_redis_client

logger = get_logger("cache_service")


class CacheBackend(Protocol):
    """Protocol for cache backends."""

    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def clear(self) -> None: ...


class InMemoryCacheBackend:
    """Thread-safe in-memory cache backend with TTL eviction."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}

    async def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        val, expiry = self._store[key]
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            return None
        return val

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = time.time() + ttl if ttl else None
        self._store[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()


class RedisCacheBackend:
    """Redis-backed distributed cache."""

    def __init__(self) -> None:
        self.client = get_redis_client()

    async def get(self, key: str) -> Any | None:
        if not self.client:
            return None
        try:
            val = await self.client.get(key)
            return json.loads(val) if val else None
        except Exception as err:
            logger.warning("redis_cache_get_error", key=key, error=str(err))
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self.client:
            return
        try:
            encoded = json.dumps(value)
            if ttl:
                await self.client.setex(key, ttl, encoded)
            else:
                await self.client.set(key, encoded)
        except Exception as err:
            logger.warning("redis_cache_set_error", key=key, error=str(err))

    async def delete(self, key: str) -> None:
        if not self.client:
            return
        try:
            await self.client.delete(key)
        except Exception as err:
            logger.warning("redis_cache_delete_error", key=key, error=str(err))

    async def clear(self) -> None:
        # In a shared redis, we avoid flushing whole db
        pass


class CacheService:
    """Application cache manager with namespacing and serialization."""

    def __init__(self, namespace: str = "app") -> None:
        self.namespace = namespace
        settings = get_settings()
        if settings.REDIS_ENABLED and get_redis_client() is not None:
            self._backend: CacheBackend = RedisCacheBackend()
        else:
            self._backend = InMemoryCacheBackend()

    def _format_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Any | None:
        return await self._backend.get(self._format_key(key))

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        settings = get_settings()
        effective_ttl = ttl or settings.REDIS_DEFAULT_TTL
        await self._backend.set(self._format_key(key), value, ttl=effective_ttl)

    async def delete(self, key: str) -> None:
        await self._backend.delete(self._format_key(key))

    async def clear(self) -> None:
        await self._backend.clear()


_cache_service = CacheService()


def get_cache_service() -> CacheService:
    """Retrieve application CacheService instance."""
    return _cache_service
