"""Integration tests for database transactions, rollbacks, and mixin behavior."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.security import hash_password
from app.db.transaction import in_transaction
from app.modules.users.models import User


async def test_transaction_commits_cleanly(db_session: AsyncSession) -> None:
    """Operations inside in_transaction must be committed upon normal block exit."""
    async with in_transaction(db_session):
        user = User(
            email="commit_test@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Commit Test",
            role=UserRole.USER,
        )
        db_session.add(user)

    # Verify user exists in fresh query
    stmt = select(User).where(User.email == "commit_test@example.com")
    res = await db_session.execute(stmt)
    persisted = res.scalars().first()
    assert persisted is not None
    assert persisted.full_name == "Commit Test"


async def test_transaction_rolls_back_on_exception(db_session: AsyncSession) -> None:
    """Operations inside in_transaction must be rolled back if an exception occurs."""
    with pytest.raises(RuntimeError, match="Simulated business failure"):
        async with in_transaction(db_session):
            user = User(
                email="rollback_test@example.com",
                hashed_password=hash_password("Pass123!"),
                full_name="Rollback Test",
                role=UserRole.USER,
            )
            db_session.add(user)
            await db_session.flush()
            raise RuntimeError("Simulated business failure")

    # Verify user was NOT committed
    stmt = select(User).where(User.email == "rollback_test@example.com")
    res = await db_session.execute(stmt)
    assert res.scalars().first() is None


async def test_soft_delete_and_restore(db_session: AsyncSession) -> None:
    """Soft-delete mixin must set deletion flags without dropping record."""
    user = User(
        email="soft_delete@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Soft Delete Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.is_deleted is False
    assert user.deleted_at is None

    # Mark deleted
    user.mark_deleted()
    await db_session.commit()

    refetched = await db_session.get(User, user.id)
    assert refetched is not None
    assert refetched.is_deleted
    assert refetched.deleted_at is not None

    # Restore
    refetched.restore()
    await db_session.commit()

    restored = await db_session.get(User, user.id)
    assert restored is not None
    assert not restored.is_deleted
    assert restored.deleted_at is None
