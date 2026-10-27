"""Explicit database transaction boundaries and atomic context managers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger("transaction")


@asynccontextmanager
async def in_transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Execute block within an explicit database transaction.

    Commits upon successful exit and rolls back on error.
    Handles existing transactions cleanly by committing upon block exit.
    """
    if session.in_transaction():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.debug("transaction_rolled_back_due_to_exception")
            raise
    else:
        async with session.begin():
            try:
                yield session
            except Exception:
                logger.debug("transaction_rolled_back_due_to_exception")
                raise
