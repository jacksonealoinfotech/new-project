"""Centralized application exception hierarchy with machine-readable error codes."""

from typing import Any

from app.core.constants import ErrorCode


class ApplicationError(Exception):
    """Base class for all application and domain exceptions."""

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = 500,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        self.headers = headers or {}


class ResourceNotFoundError(ApplicationError):
    """Raised when an entity or resource could not be found."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: Any = None,
        message: str | None = None,
        details: Any = None,
    ) -> None:
        msg = message or (
            f"{resource} with identifier '{identifier}' was not found."
            if identifier
            else f"{resource} not found."
        )
        super().__init__(
            message=msg,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            details=details,
        )


class ResourceConflictError(ApplicationError):
    """Raised when a unique constraint or conflicting state is violated."""

    def __init__(
        self,
        message: str = "A conflicting resource already exists.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_CONFLICT,
            status_code=409,
            details=details,
        )


class AuthenticationError(ApplicationError):
    """Raised when credentials are invalid or missing."""

    def __init__(
        self,
        message: str = "Could not validate authentication credentials.",
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        hdr = headers or {"WWW-Authenticate": "Bearer"}
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_FAILED,
            status_code=401,
            details=details,
            headers=hdr,
        )


class PermissionDeniedError(ApplicationError):
    """Raised when an authenticated principal lacks required permissions."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=403,
            details=details,
        )


class ValidationError(ApplicationError):
    """Raised when domain or business rule validation fails."""

    def __init__(
        self,
        message: str = "Validation failed.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details=details,
        )


class RateLimitExceededError(ApplicationError):
    """Raised when client exceeds designated request rate limits."""

    def __init__(
        self,
        retry_after: int = 60,
        message: str = "Rate limit exceeded. Please try again later.",
        details: Any = None,
    ) -> None:
        headers = {"Retry-After": str(retry_after)}
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details=details,
            headers=headers,
        )


class IdempotencyConflictError(ApplicationError):
    """Raised when an idempotency key is reused with a different request payload or is concurrently in-flight."""

    def __init__(
        self,
        message: str = "Idempotency key conflict: request is already processing or payload mismatch.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.IDEMPOTENCY_CONFLICT,
            status_code=409,
            details=details,
        )


class ConcurrencyConflictError(ApplicationError):
    """Raised when optimistic concurrency checks fail due to concurrent updates."""

    def __init__(
        self,
        message: str = "Resource was modified by another operation. Please re-fetch and retry.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.CONCURRENCY_CONFLICT,
            status_code=409,
            details=details,
        )


class DatabaseUnavailableError(ApplicationError):
    """Raised when database connection cannot be acquired or timed out."""

    def __init__(
        self,
        message: str = "Database service is temporarily unavailable.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_UNAVAILABLE,
            status_code=503,
            details=details,
        )


class ExternalServiceError(ApplicationError):
    """Raised when an external third-party integration fails."""

    def __init__(
        self,
        service_name: str,
        message: str = "External service failed to process request.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=f"{service_name}: {message}",
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=502,
            details=details,
        )


class BadRequestError(ApplicationError):
    """Raised for malformed request parameters or preconditions."""

    def __init__(
        self,
        message: str = "Bad request.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.BAD_REQUEST,
            status_code=400,
            details=details,
        )
