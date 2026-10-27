"""Unit tests for offset and cursor pagination algorithms."""

import pytest

from app.core.exceptions import BadRequestError
from app.core.pagination import (
    PaginatedResponse,
    PaginationParams,
    decode_cursor,
    encode_cursor,
)


def test_pagination_params_offset_and_limit() -> None:
    """Pagination parameters offset must map accurately to page and page_size."""
    params = PaginationParams(page=1, page_size=20)
    assert params.offset == 0
    assert params.limit == 20

    params2 = PaginationParams(page=3, page_size=15)
    assert params2.offset == 30
    assert params2.limit == 15


def test_paginated_response_metadata_calculation() -> None:
    """PaginatedResponse metadata must calculate total_pages and navigation flags correctly."""
    params = PaginationParams(page=1, page_size=20)
    res = PaginatedResponse.create(items=[1, 2, 3], total_items=45, params=params)

    assert res.meta.page == 1
    assert res.meta.page_size == 20
    assert res.meta.total_items == 45
    assert res.meta.total_pages == 3
    assert res.meta.has_next is True
    assert res.meta.has_previous is False


def test_paginated_response_zero_results() -> None:
    """Zero total items should report 0 total pages and false for next/previous."""
    params = PaginationParams(page=1, page_size=20)
    res: PaginatedResponse[int] = PaginatedResponse.create(items=[], total_items=0, params=params)

    assert res.meta.total_pages == 0
    assert res.meta.has_next is False
    assert res.meta.has_previous is False


def test_cursor_encoding_and_decoding() -> None:
    """Opaque cursor encoding must roundtrip and decode deterministically."""
    data = {"id": "123", "created_at": "2026-01-01T00:00:00"}
    cursor = encode_cursor(data)
    decoded = decode_cursor(cursor)

    assert decoded == data


def test_malformed_cursor_rejection() -> None:
    """Invalid cursor string must raise BadRequestError."""
    with pytest.raises(BadRequestError, match="Malformed or invalid cursor"):
        decode_cursor("invalid-not-base64-content!@#$")
