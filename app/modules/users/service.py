"""User domain application service coordinating business logic and database transactions."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.security import hash_password
from app.db.transaction import in_transaction
from app.modules.users.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserAdminCreate,
    UserAdminUpdate,
    UserCreate,
    UserFilterParams,
    UserResponse,
    UserUpdate,
)


class UserService:
    """Application service for User domain operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        """Fetch user by ID or raise UserNotFoundError."""
        user = await self.repository.get(user_id)
        if not user or user.is_deleted:
            raise UserNotFoundError(identifier=user_id)
        return user

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by email."""
        return await self.repository.get_by_email(email)

    async def create_user(self, data: UserCreate) -> User:
        """Register a standard user account."""
        existing = await self.repository.get_by_email(data.email)
        if existing:
            raise UserAlreadyExistsError(email=data.email)

        async with in_transaction(self.session):
            user = User(
                email=data.email,
                hashed_password=hash_password(data.password),
                full_name=data.full_name,
            )
            created = await self.repository.create(user)
            return created

    async def create_admin_user(self, data: UserAdminCreate) -> User:
        """Create a user with explicit administrative role and status."""
        existing = await self.repository.get_by_email(data.email)
        if existing:
            raise UserAlreadyExistsError(email=data.email)

        async with in_transaction(self.session):
            user = User(
                email=data.email,
                hashed_password=hash_password(data.password),
                full_name=data.full_name,
                role=data.role,
                is_active=data.is_active,
                is_verified=data.is_verified,
            )
            created = await self.repository.create(user)
            return created

    async def list_users(
        self,
        pagination: PaginationParams,
        filters: UserFilterParams | None = None,
    ) -> PaginatedResponse[UserResponse]:
        """Fetch paginated, filtered user accounts."""
        items, total = await self.repository.list_filtered(
            offset=pagination.offset,
            limit=pagination.limit,
            filters=filters,
        )
        user_responses = [UserResponse.model_validate(item) for item in items]
        return PaginatedResponse.create(
            items=user_responses,
            total_items=total,
            params=pagination,
        )

    async def update_profile(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        """Self-service user profile update."""
        user = await self.get_by_id(user_id)
        async with in_transaction(self.session):
            user.version += 1
            updated = await self.repository.update(user, data)
            return updated

    async def admin_update_user(self, user_id: uuid.UUID, data: UserAdminUpdate) -> User:
        """Privileged administrative user update."""
        user = await self.get_by_id(user_id)
        async with in_transaction(self.session):
            user.version += 1
            updated = await self.repository.update(user, data)
            return updated

    async def soft_delete_user(self, user_id: uuid.UUID) -> None:
        """Soft-delete user account."""
        user = await self.get_by_id(user_id)
        async with in_transaction(self.session):
            user.mark_deleted()
            await self.session.flush()
