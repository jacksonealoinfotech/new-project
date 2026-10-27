"""Async database engine, session factory, and connection lifecycle management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("db_session")

# Module-level engine and session factory holders (initialized in init_db or lifecycle)
_async_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Retrieve or initialize the singleton AsyncEngine."""
    global _async_engine, _session_factory
    if _async_engine is None:
        settings = get_settings()
        url = settings.DATABASE_URL

        # Specialized pool configuration based on database dialect
        is_sqlite = url.startswith("sqlite")
        engine_kwargs: dict[str, object] = {
            "echo": settings.DATABASE_ECHO,
        }

        if is_sqlite:
            # NullPool for SQLite avoids cross-thread locking and concurrency issues
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update(
                {
                    "pool_size": settings.DATABASE_POOL_SIZE,
                    "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                    "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
                    "pool_recycle": settings.DATABASE_POOL_RECYCLE,
                    "pool_pre_ping": True,
                }
            )

        _async_engine = create_async_engine(url, **engine_kwargs)
        _session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        logger.info("database_engine_initialized", dialect="sqlite" if is_sqlite else "postgresql")

    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve session factory."""
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI request-scoped dependency providing an AsyncSession.

    Transactions are explicitly controlled by application services or context managers.
    Rolls back automatically upon unhandled exceptions.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> bool:
    """Execute a lightweight health check query against the database."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as err:
        logger.error("database_health_check_failed", error=str(err))
        return False


async def dispose_engine() -> None:
    """Dispose engine connections during application shutdown."""
    global _async_engine, _session_factory
    if _async_engine is not None:
        logger.info("disposing_database_engine")
        await _async_engine.dispose()
        _async_engine = None
        _session_factory = None
