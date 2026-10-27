"""Standardized API response models and contracts."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.constants import ErrorCode

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    """Detailed error object contained in error responses."""

    code: ErrorCode | str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable explanation of the error")
    details: Any = Field(
        default=None, description="Optional granular validation or contextual details"
    )
    request_id: str | None = Field(default=None, description="Request tracking identifier")


class ErrorResponse(BaseModel):
    """Standardized root error contract across all endpoints."""

    error: ErrorDetail


class MessageResponse(BaseModel):
    """Standard response model for operations returning a simple status message."""

    message: str = Field(description="Operational status message")


class SuccessResponse(BaseModel, Generic[DataT]):
    """Optional generic envelope for data responses where explicitly needed."""

    data: DataT
    message: str | None = None
