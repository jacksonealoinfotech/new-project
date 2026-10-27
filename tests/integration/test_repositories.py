"""Integration tests for generic BaseRepository and domain UserRepository."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserFilterParams


async def test_user_repository_crud_lifecycle(db_session: AsyncSession) -> None:
    """UserRepository must perform get, create, update, delete, and exists queries accurately."""
    repo = UserRepository(db_session)

    # 1. Create
    user = User(
        email="repo_user@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Repo User",
    )
    created = await repo.create(user)
    await db_session.commit()
    assert created.id is not None

    # 2. Get by ID & Get by Email
    fetched = await repo.get(created.id)
    assert fetched is not None
    assert fetched.email == "repo_user@example.com"

    by_email = await repo.get_by_email("REPO_USER@example.com")
    assert by_email is not None
    assert by_email.id == created.id

    # 3. Exists
    exists = await repo.exists(email="repo_user@example.com")
    assert exists is True

    # 4. Update
    await repo.update(fetched, {"full_name": "Updated Name"})
    await db_session.commit()
    refreshed = await repo.get(created.id)
    assert refreshed is not None
    assert refreshed.full_name == "Updated Name"

    # 5. Delete
    await repo.delete(refreshed)
    await db_session.commit()
    deleted = await repo.get(created.id)
    assert deleted is None


async def test_user_repository_filtered_pagination(db_session: AsyncSession) -> None:
    """list_filtered must support role filtering, search, and pagination limits."""
    repo = UserRepository(db_session)

    # Create users
    u1 = User(
        email="alice@tech.org",
        hashed_password=hash_password("P!"),
        full_name="Alice Smith",
        role=UserRole.ADMIN,
    )
    u2 = User(
        email="bob@tech.org",
        hashed_password=hash_password("P!"),
        full_name="Bob Jones",
        role=UserRole.USER,
    )
    u3 = User(
        email="charlie@other.org",
        hashed_password=hash_password("P!"),
        full_name="Charlie Brown",
        role=UserRole.USER,
    )
    db_session.add_all([u1, u2, u3])
    await db_session.commit()

    # Filter by Admin role
    admins, total_admins = await repo.list_filtered(
        offset=0, limit=10, filters=UserFilterParams(role=UserRole.ADMIN)
    )
    assert total_admins == 1
    assert admins[0].email == "alice@tech.org"

    # Search by full name substring
    search_res, search_total = await repo.list_filtered(
        offset=0, limit=10, filters=UserFilterParams(search="smith")
    )
    assert search_total == 1
    assert search_res[0].email == "alice@tech.org"


async def test_database_enforces_unique_email_constraint(db_session: AsyncSession) -> None:
    """Inserting duplicate email must raise IntegrityError at the database level."""
    repo = UserRepository(db_session)
    u1 = User(
        email="duplicate@example.com",
        hashed_password=hash_password("P!"),
        full_name="User 1",
    )
    await repo.create(u1)
    await db_session.commit()

    u2 = User(
        email="duplicate@example.com",
        hashed_password=hash_password("P!"),
        full_name="User 2",
    )
    with pytest.raises(IntegrityError):
        await repo.create(u2)
        await db_session.commit()
