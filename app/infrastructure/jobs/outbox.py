"""Transactional Outbox pattern implementation for reliable asynchronous event delivery."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import OutboxStatus
from app.core.logging import get_logger
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.transaction import in_transaction

logger = get_logger("outbox")


class OutboxMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted event record coordinated within identical database transactions as state changes."""

    __tablename__ = "outbox_messages"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, native_enum=False, length=50),
        default=OutboxStatus.PENDING,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class OutboxRepository:
    """Repository handling persistence and state updates of outbox events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(self, event_type: str, payload: dict[str, Any]) -> OutboxMessage:
        """Enqueue an event within the current session/transaction."""
        message = OutboxMessage(
            event_type=event_type,
            payload=json.dumps(payload),
            status=OutboxStatus.PENDING,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def fetch_pending(self, limit: int = 50) -> list[OutboxMessage]:
        """Retrieve batch of ready pending messages."""
        now = datetime.now(UTC)
        stmt = (
            select(OutboxMessage)
            .where(
                OutboxMessage.status == OutboxStatus.PENDING,
                OutboxMessage.scheduled_at <= now,
            )
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def mark_published(self, message: OutboxMessage) -> None:
        message.status = OutboxStatus.PUBLISHED
        await self.session.flush()

    async def mark_failed(self, message: OutboxMessage, error: str) -> None:
        message.retry_count += 1
        message.error_message = error
        if message.retry_count >= 5:
            message.status = OutboxStatus.FAILED
        else:
            message.status = OutboxStatus.PENDING
        await self.session.flush()


class OutboxDispatcher:
    """Background publisher service delivering pending outbox messages."""

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory

    async def dispatch_batch(self, limit: int = 50) -> int:
        """Process one batch of pending messages."""
        count = 0
        async with self.session_factory() as session:
            repo = OutboxRepository(session)
            pending = await repo.fetch_pending(limit=limit)
            for msg in pending:
                async with in_transaction(session):
                    try:
                        logger.info(
                            "publishing_outbox_event",
                            event_type=msg.event_type,
                            message_id=str(msg.id),
                        )
                        # Dispatch logic to message broker or webhook consumer goes here
                        await repo.mark_published(msg)
                        count += 1
                    except Exception as err:
                        logger.exception("outbox_publish_failed", message_id=str(msg.id))
                        await repo.mark_failed(msg, str(err))
        return count
