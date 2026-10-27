"""Shared utility functions."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)


def sanitize_string(val: str) -> str:
    """Strip surrounding whitespace and normalize empty strings."""
    return val.strip()
