"""Reusable resilient HTTP client using HTTPX with pooling and backoff."""

import asyncio
import random
from typing import Any

import httpx

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger("http_client")

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Retrieve or initialize shared async HTTP client with connection pooling."""
    global _http_client
    if _http_client is None:
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        timeout = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
        _http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
        logger.info("shared_http_client_initialized")
    return _http_client


async def close_http_client() -> None:
    """Close shared HTTP client on shutdown."""
    global _http_client
    if _http_client is not None:
        logger.info("closing_shared_http_client")
        await _http_client.aclose()
        _http_client = None


class ResilientHttpClient:
    """Wraps HTTP operations with timeouts, error classification, and exponential backoff."""

    def __init__(self, service_name: str, base_url: str = "") -> None:
        self.service_name = service_name
        self.base_url = base_url

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        max_retries: int = 3,
    ) -> httpx.Response:
        """Perform GET request with exponential backoff on transient failures."""
        client = get_http_client()
        target_url = f"{self.base_url}{url}" if self.base_url else url

        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await client.get(target_url, params=params, headers=headers)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as err:
                last_err = err
                # Only retry 5xx server errors or network timeouts
                if isinstance(err, httpx.HTTPStatusError) and err.response.status_code < 500:
                    raise ExternalServiceError(
                        service_name=self.service_name,
                        message=f"Request failed with status {err.response.status_code}",
                        details=err.response.text,
                    ) from err

                if attempt < max_retries - 1:
                    sleep_time = (2**attempt) + random.uniform(0.1, 0.5)  # noqa: S311
                    logger.warning(
                        "http_request_retrying",
                        service=self.service_name,
                        attempt=attempt + 1,
                        sleep_seconds=round(sleep_time, 2),
                    )
                    await asyncio.sleep(sleep_time)

        raise ExternalServiceError(
            service_name=self.service_name,
            message="External call failed after retries exhausted.",
            details=str(last_err),
        )
