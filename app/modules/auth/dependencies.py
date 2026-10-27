"""Authentication and authorization FastAPI dependency providers."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

http_bearer = HTTPBearer(auto_error=False)


def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    """Provide initialized AuthService instance."""
    auth_repo = AuthRepository(session)
    user_repo = UserRepository(session)
    return AuthService(auth_repo=auth_repo, user_repo=user_repo)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Extract and validate Bearer JWT token, returning the authenticated User."""
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Authorization header is missing or invalid.")

    payload = decode_access_token(credentials.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Invalid token subject.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Malformed user identifier in token.") from None

    user_repo = UserRepository(session)
    user = await user_repo.get(user_uuid)
    if not user or user.is_deleted:
        raise AuthenticationError("User associated with this token does not exist.")

    # Bind user_id to request state for rate limiting and logging context
    request.state.user_id = str(user.id)
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Verify that current user account is active."""
    if not user.is_active:
        raise AuthenticationError("User account has been deactivated.")
    return user


def require_role(*allowed_roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Factory creating dependency enforcing that the user has at least one of the allowed roles."""

    async def _role_checker(user: User = Depends(get_current_active_user)) -> User:
        # SUPERUSER always has access
        if user.role == UserRole.SUPERUSER or user.role in allowed_roles:
            return user
        raise PermissionDeniedError(
            f"Insufficient privileges. Required role(s): {[r.value for r in allowed_roles]}"
        )

    return _role_checker
