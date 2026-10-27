"""Production HTTP middleware: request IDs, structured logging, and security headers."""

import json
import time
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.constants import HeaderName
from app.core.error_handlers import application_error_handler
from app.core.exceptions import ApplicationError
from app.core.idempotency import check_idempotency, store_idempotency_response
from app.core.logging import get_logger

logger = get_logger("http_access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns unique request IDs, binds logging contextvars, and records request telemetry."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        # Extract or generate unique request ID
        req_id = request.headers.get(HeaderName.REQUEST_ID)
        if not req_id:
            req_id = f"req_{uuid.uuid4().hex}"

        request.state.request_id = req_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=req_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(
                "request_failed_with_exception",
                duration_ms=round(duration_ms, 2),
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers[HeaderName.REQUEST_ID] = req_id

        # Attach rate-limit headers if present in request state
        if hasattr(request.state, "rate_limit_limit"):
            response.headers[HeaderName.RATE_LIMIT_LIMIT] = str(request.state.rate_limit_limit)
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers[HeaderName.RATE_LIMIT_REMAINING] = str(
                request.state.rate_limit_remaining
            )

        # Log access event
        logger.info(
            "http_request_finished",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=request.client.host if request.client else "unknown",
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces standard HTTP security defense-in-depth headers on all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response: Response = await call_next(request)
        settings = get_settings()

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        if settings.APP_ENV.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; frame-ancestors 'none';"
            )

        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Enforces idempotency on mutating operations when Idempotency-Key header is supplied."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        idempotency_key = request.headers.get(HeaderName.IDEMPOTENCY_KEY)
        if request.method in ("POST", "PATCH", "PUT") and idempotency_key:
            try:
                cached = await check_idempotency(request)
            except ApplicationError as exc:
                return await application_error_handler(request, exc)

            if cached is not None:
                return cached

            response: Response = await call_next(request)

            # Buffer response body to cache payload
            body_iterator = getattr(response, "body_iterator", None)
            if body_iterator is not None:
                response_chunks = [chunk async for chunk in body_iterator]
                response.body_iterator = iterate_in_threadpool(iter(response_chunks))  # type: ignore[attr-defined]
                body_bytes = b"".join(response_chunks)
            else:
                body_bytes = getattr(response, "body", b"")

            try:
                parsed_data = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                parsed_data = None

            store_idempotency_response(
                request=request,
                status_code=response.status_code,
                headers=dict(response.headers),
                response_data=parsed_data,
            )
            return response

        return await call_next(request)


def register_middlewares(app: FastAPI) -> None:
    """Register core application middlewares."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(RequestContextMiddleware)
