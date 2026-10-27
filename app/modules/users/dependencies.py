"""User module dependency providers."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    """Provide UserRepository instance bound to current database session."""
    return UserRepository(session)


def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    """Provide UserService instance bound to current database session."""
    return UserService(session)
