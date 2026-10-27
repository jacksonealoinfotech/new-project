"""Reusable SQLAlchemy 2.x model mixins for identifiers, audit timestamps, and concurrency."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Provides a UUID v4 primary key column compatible with both PostgreSQL and SQLite."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """Provides UTC-aware created_at and updated_at audit timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """Enables soft deletion flags and audit timestamp without permanent record destruction."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    def mark_deleted(self) -> None:
        """Mark record as soft-deleted with current UTC timestamp."""
        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class VersionMixin:
    """Enables optimistic concurrency control by tracking record version increments."""

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
