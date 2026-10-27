"""Pytest configuration and test fixtures providing isolated database and HTTP clients."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.common.enums import UserRole
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.modules.users.models import User

# In-memory SQLite async engine with StaticPool ensures the in-memory database persists across connections in a test
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def prepare_database() -> AsyncGenerator[None, None]:
    """Create all schema tables before each test and reset in-memory state."""
    from app.core.idempotency import _in_memory_idempotency_store
    from app.core.rate_limit import _in_memory_limiter

    _in_memory_limiter._requests.clear()
    _in_memory_idempotency_store._records.clear()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    _in_memory_limiter._requests.clear()
    _in_memory_idempotency_store._records.clear()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for test execution."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def app_instance(db_session: AsyncSession) -> FastAPI:
    """FastAPI application instance with database dependency overridden for tests."""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    return app


@pytest.fixture
async def client(app_instance: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client configured with ASGI transport for testing endpoints."""
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create and persist a standard regular user fixture."""
    user = User(
        email="user@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Regular Test User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create and persist an administrative user fixture."""
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        full_name="Admin Test User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def user_auth_headers(test_user: User) -> dict[str, str]:
    """Provide Authorization header for the regular user."""
    token = create_access_token(subject=str(test_user.id), roles=[test_user.role.value])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_admin: User) -> dict[str, str]:
    """Provide Authorization header for the admin user."""
    token = create_access_token(subject=str(test_admin.id), roles=[test_admin.role.value])
    return {"Authorization": f"Bearer {token}"}
