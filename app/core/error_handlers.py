"""Centralized exception handlers mapping application errors to standardized API contracts."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from app.core.constants import ErrorCode, HeaderName
from app.core.exceptions import ApplicationError
from app.core.logging import get_logger

logger = get_logger("error_handler")


def _get_request_id(request: Request) -> str | None:
    """Retrieve tracking request ID from request state or headers."""
    if hasattr(request.state, "request_id"):
        return str(request.state.request_id)
    return request.headers.get(HeaderName.REQUEST_ID)


def _format_error_response(
    code: str,
    message: str,
    request_id: str | None,
    details: Any = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Construct consistent JSON error response."""
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """Handle custom application and domain exceptions."""
    req_id = _get_request_id(request)
    logger.warning(
        "application_error",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=req_id,
        path=request.url.path,
    )
    return _format_error_response(
        code=exc.error_code,
        message=exc.message,
        request_id=req_id,
        details=exc.details,
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI/Pydantic request validation errors."""
    req_id = _get_request_id(request)
    formatted_errors = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []))
        formatted_errors.append(
            {
                "field": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
        )

    logger.info(
        "request_validation_failed",
        errors=formatted_errors,
        request_id=req_id,
        path=request.url.path,
    )
    return _format_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed. Check 'details' for field-level errors.",
        request_id=req_id,
        details=formatted_errors,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard Starlette/FastAPI HTTPExceptions."""
    req_id = _get_request_id(request)
    code = ErrorCode.BAD_REQUEST
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = ErrorCode.AUTHENTICATION_FAILED
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = ErrorCode.PERMISSION_DENIED
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        code = ErrorCode.RESOURCE_NOT_FOUND
    elif exc.status_code == status.HTTP_409_CONFLICT:
        code = ErrorCode.RESOURCE_CONFLICT
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        code = ErrorCode.RATE_LIMIT_EXCEEDED

    return _format_error_response(
        code=code,
        message=str(exc.detail),
        request_id=req_id,
        status_code=exc.status_code,
        headers=dict(exc.headers) if exc.headers else None,
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity constraint violations safely without leaking SQL internals."""
    req_id = _get_request_id(request)
    orig_msg = str(exc.orig).lower() if exc.orig else ""

    logger.warning(
        "database_integrity_violation",
        request_id=req_id,
        path=request.url.path,
        error_detail=str(exc.orig),
    )

    if "unique" in orig_msg or "duplicate" in orig_msg:
        message = "A conflicting resource with unique constraints already exists."
        code = ErrorCode.RESOURCE_CONFLICT
        http_status = status.HTTP_409_CONFLICT
    elif "foreign key" in orig_msg:
        message = "Operation referenced a non-existent related record."
        code = ErrorCode.BAD_REQUEST
        http_status = status.HTTP_400_BAD_REQUEST
    else:
        message = "Database integrity constraint violation."
        code = ErrorCode.RESOURCE_CONFLICT
        http_status = status.HTTP_409_CONFLICT

    return _format_error_response(
        code=code,
        message=message,
        request_id=req_id,
        status_code=http_status,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions ensuring no stack traces leak in API responses."""
    req_id = _get_request_id(request)
    logger.exception(
        "unhandled_internal_server_error",
        error=str(exc),
        request_id=req_id,
        path=request.url.path,
    )
    return _format_error_response(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="An internal server error occurred. Please contact support with the request ID.",
        request_id=req_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers on the FastAPI application."""
    app.add_exception_handler(ApplicationError, application_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
