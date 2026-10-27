"""Rate limiting infrastructure supporting both in-memory and Redis backends."""

import time
from collections import defaultdict
from typing import Protocol

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitExceededError


class RateLimiterBackend(Protocol):
    """Protocol defining the rate limiter interface."""

    async def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int, int]:
        """Check if request is allowed. Returns (allowed, remaining, retry_after)."""
        ...


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter for development and single-process environments."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - window_seconds

        # Filter out expired timestamps
        timestamps = [ts for ts in self._requests[key] if ts > window_start]
        self._requests[key] = timestamps

        if len(timestamps) >= max_requests:
            oldest_ts = timestamps[0]
            retry_after = max(1, int(oldest_ts + window_seconds - now))
            return False, 0, retry_after

        # Record new request
        self._requests[key].append(now)
        remaining = max(0, max_requests - len(self._requests[key]))
        return True, remaining, 0


# Global in-memory rate limiter instance
_in_memory_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> RateLimiterBackend:
    """Return the configured rate limiter backend."""
    # When Redis integration is active and enabled, return RedisRateLimiter.
    # Defaulting to InMemoryRateLimiter ensures reliable standalone operation.
    return _in_memory_limiter


def get_client_identifier(request: Request) -> str:
    """Extract client identity: prefer authenticated user ID if present, otherwise client IP."""
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "unknown"

    return f"ip:{client_ip}"


class RateLimitDependency:
    """FastAPI dependency for declaring rate limits on endpoints."""

    def __init__(self, max_requests: int | None = None, window_seconds: int | None = None) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED:
            return

        max_req = self.max_requests or settings.RATE_LIMIT_DEFAULT_REQUESTS
        window_sec = self.window_seconds or settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS

        client_id = get_client_identifier(request)
        route_key = f"{request.method}:{request.url.path}:{client_id}"

        limiter = get_rate_limiter()
        allowed, remaining, retry_after = await limiter.is_allowed(route_key, max_req, window_sec)

        request.state.rate_limit_limit = max_req
        request.state.rate_limit_remaining = remaining

        if not allowed:
            raise RateLimitExceededError(
                retry_after=retry_after,
                details={
                    "limit": max_req,
                    "window_seconds": window_sec,
                    "retry_after": retry_after,
                },
            )


def rate_limit(
    max_requests: int | None = None, window_seconds: int | None = None
) -> RateLimitDependency:
    """Helper factory for rate limit dependencies."""
    return RateLimitDependency(max_requests=max_requests, window_seconds=window_seconds)
