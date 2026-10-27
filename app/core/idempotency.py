"""Idempotency management ensuring safe retries of mutating API operations."""

import hashlib
import time
from typing import Any

from fastapi import Request, Response
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.constants import HeaderName
from app.core.exceptions import IdempotencyConflictError
from app.core.rate_limit import get_client_identifier


class IdempotencyRecord:
    """Stored record of an idempotent request execution."""

    def __init__(
        self,
        fingerprint: str,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        response_data: Any = None,
        is_processing: bool = True,
        created_at: float | None = None,
    ) -> None:
        self.fingerprint = fingerprint
        self.status_code = status_code
        self.headers = headers or {}
        self.response_data = response_data
        self.is_processing = is_processing
        self.created_at = created_at or time.time()


class InMemoryIdempotencyStore:
    """Thread-safe in-memory store for idempotency keys."""

    def __init__(self) -> None:
        self._records: dict[str, IdempotencyRecord] = {}

    def get(self, key: str) -> IdempotencyRecord | None:
        record = self._records.get(key)
        if not record:
            return None
        settings = get_settings()
        if time.time() - record.created_at > settings.IDEMPOTENCY_EXPIRE_SECONDS:
            del self._records[key]
            return None
        return record

    def set(self, key: str, record: IdempotencyRecord) -> None:
        self._records[key] = record

    def delete(self, key: str) -> None:
        self._records.pop(key, None)


_in_memory_idempotency_store = InMemoryIdempotencyStore()


def compute_request_fingerprint(method: str, path: str, body: bytes) -> str:
    """Compute deterministic SHA-256 fingerprint from method, path, and request body bytes."""
    hasher = hashlib.sha256()
    hasher.update(method.encode("utf-8"))
    hasher.update(b":")
    hasher.update(path.encode("utf-8"))
    hasher.update(b":")
    hasher.update(body)
    return hasher.hexdigest()


async def check_idempotency(request: Request) -> Response | None:
    """Check Idempotency-Key header. If previously completed, return cached response directly.

    If in-progress or payload conflict, raise IdempotencyConflictError.
    """
    idempotency_key = request.headers.get(HeaderName.IDEMPOTENCY_KEY)
    if not idempotency_key:
        return None

    client_id = get_client_identifier(request)
    store_key = f"idempotency:{client_id}:{idempotency_key}"

    body = await request.body()
    fingerprint = compute_request_fingerprint(request.method, request.url.path, body)

    record = _in_memory_idempotency_store.get(store_key)
    if record:
        if record.fingerprint != fingerprint:
            raise IdempotencyConflictError(
                message="Idempotency key was previously used with a different request payload."
            )
        if record.is_processing:
            raise IdempotencyConflictError(
                message="A request with this idempotency key is currently processing. Please wait."
            )
        # Return previously cached response
        return JSONResponse(
            status_code=record.status_code or 200,
            content=record.response_data,
            headers={**record.headers, "X-Cache-Lookup": "HIT-IDEMPOTENT"},
        )

    # Mark as in-flight
    _in_memory_idempotency_store.set(
        store_key,
        IdempotencyRecord(fingerprint=fingerprint, is_processing=True),
    )
    request.state.idempotency_store_key = store_key
    request.state.idempotency_fingerprint = fingerprint
    return None


def store_idempotency_response(
    request: Request,
    status_code: int,
    headers: dict[str, str],
    response_data: Any,
) -> None:
    """Store the completed response for the given idempotency key."""
    store_key = getattr(request.state, "idempotency_store_key", None)
    fingerprint = getattr(request.state, "idempotency_fingerprint", None)
    if store_key and fingerprint:
        # Cache only successful / client responses (2xx, 4xx) - don't cache 5xx server errors
        if status_code < 500:
            _in_memory_idempotency_store.set(
                store_key,
                IdempotencyRecord(
                    fingerprint=fingerprint,
                    status_code=status_code,
                    headers=headers,
                    response_data=response_data,
                    is_processing=False,
                ),
            )
        else:
            _in_memory_idempotency_store.delete(store_key)
