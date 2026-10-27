"""Unit tests for exception hierarchy and error payload serialization."""

from app.core.constants import ErrorCode
from app.core.exceptions import (
    ApplicationError,
    AuthenticationError,
    RateLimitExceededError,
    ResourceNotFoundError,
)
from app.core.responses import ErrorDetail, ErrorResponse


def test_application_error_defaults() -> None:
    """Base application exception should default to 500 status and INTERNAL_SERVER_ERROR."""
    err = ApplicationError("Something failed")
    assert err.status_code == 500
    assert err.error_code == ErrorCode.INTERNAL_SERVER_ERROR
    assert err.message == "Something failed"


def test_resource_not_found_error() -> None:
    """ResourceNotFoundError must populate 404 status and RESOURCE_NOT_FOUND code."""
    err = ResourceNotFoundError(resource="User", identifier="123")
    assert err.status_code == 404
    assert err.error_code == ErrorCode.RESOURCE_NOT_FOUND
    assert "User with identifier '123' was not found" in err.message


def test_rate_limit_exceeded_error_headers() -> None:
    """RateLimitExceededError must supply Retry-After header and 429 status code."""
    err = RateLimitExceededError(retry_after=45)
    assert err.status_code == 429
    assert err.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
    assert err.headers.get("Retry-After") == "45"


def test_authentication_error_headers() -> None:
    """AuthenticationError must supply WWW-Authenticate header and 401 status code."""
    err = AuthenticationError("Invalid token")
    assert err.status_code == 401
    assert err.error_code == ErrorCode.AUTHENTICATION_FAILED
    assert err.headers.get("WWW-Authenticate") == "Bearer"


def test_error_response_contract_serialization() -> None:
    """ErrorResponse model must match standardized JSON structure."""
    detail = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Item not found",
        details={"item_id": 42},
        request_id="req_test_123",
    )
    resp = ErrorResponse(error=detail)
    dumped = resp.model_dump()

    assert dumped["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert dumped["error"]["message"] == "Item not found"
    assert dumped["error"]["details"] == {"item_id": 42}
    assert dumped["error"]["request_id"] == "req_test_123"
