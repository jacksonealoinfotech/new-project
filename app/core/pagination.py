"""Reusable pagination infrastructure for offset and cursor-based access."""

import base64
import json
import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE
from app.core.exceptions import BadRequestError

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameter model for offset-based pagination."""

    page: int = Field(default=DEFAULT_PAGE, ge=1, description="Page number starting at 1")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description="Number of items per page",
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginationMeta(BaseModel):
    """Metadata payload describing offset pagination state."""

    page: int = Field(description="Current page number")
    page_size: int = Field(description="Current page size limit")
    total_items: int = Field(description="Total number of items matching criteria")
    total_pages: int = Field(description="Total number of available pages")
    has_next: bool = Field(description="True if next page exists")
    has_previous: bool = Field(description="True if previous page exists")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized envelope for offset-paginated resource collections."""

    items: list[T] = Field(description="List of records for current page")
    meta: PaginationMeta = Field(description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: list[T],
        total_items: int,
        params: PaginationParams,
    ) -> "PaginatedResponse[T]":
        """Construct a paginated response instance from items and pagination params."""
        total_pages = math.ceil(total_items / params.page_size) if total_items > 0 else 0
        has_next = params.page < total_pages
        has_previous = params.page > 1 and total_pages > 0

        meta = PaginationMeta(
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )
        return cls(items=items, meta=meta)


class CursorPaginationParams(BaseModel):
    """Query parameter model for cursor-based pagination."""

    cursor: str | None = Field(default=None, description="Opaque cursor string for navigation")
    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE)


class CursorPaginationMeta(BaseModel):
    """Metadata payload for cursor navigation."""

    next_cursor: str | None = Field(default=None, description="Cursor for the subsequent page")
    previous_cursor: str | None = Field(default=None, description="Cursor for previous page")
    has_next: bool = Field(description="True if subsequent page exists")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Standardized envelope for cursor-paginated resource collections."""

    items: list[T]
    meta: CursorPaginationMeta


def encode_cursor(data: dict[str, Any]) -> str:
    """Encode cursor dict data into an opaque URL-safe base64 string."""
    json_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8")


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode and validate an opaque cursor string."""
    try:
        json_bytes = base64.urlsafe_b64decode(cursor.encode("utf-8"))
        data: dict[str, Any] = json.loads(json_bytes.decode("utf-8"))
        return data
    except Exception as err:
        raise BadRequestError(message=f"Malformed or invalid cursor provided: {err!s}") from None
