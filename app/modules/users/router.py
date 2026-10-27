"""User management REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, status

from app.common.enums import UserRole
from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.responses import MessageResponse
from app.modules.auth.dependencies import get_current_active_user, require_role
from app.modules.users.dependencies import get_user_service
from app.modules.users.models import User
from app.modules.users.permissions import (
    check_can_view_user,
)
from app.modules.users.schemas import (
    UserAdminCreate,
    UserAdminUpdate,
    UserFilterParams,
    UserResponse,
    UserUpdate,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Retrieve profile details for the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
)
async def update_current_user_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Update profile attributes for the currently authenticated user."""
    updated = await service.update_profile(current_user.id, data)
    return UserResponse.model_validate(updated)


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    summary="List users (Admin only)",
)
async def list_users(
    pagination: PaginationParams = Depends(),
    filters: UserFilterParams = Depends(),
    service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserResponse]:
    """Retrieve paginated and filtered list of user accounts. Requires admin role."""
    return await service.list_users(pagination=pagination, filters=filters)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    summary="Create user (Admin only)",
)
async def create_user_admin(
    data: UserAdminCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Privileged endpoint for administrators to create users with explicit roles."""
    user = await service.create_admin_user(data)
    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Retrieve user details by ID. Restricted to account owners and administrators."""
    check_can_view_user(current_user, user_id)
    user = await service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    summary="Update user attributes (Admin only)",
)
async def admin_update_user(
    user_id: uuid.UUID,
    data: UserAdminUpdate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Update user role, status, or details. Restricted to administrators."""
    updated = await service.admin_update_user(user_id, data)
    return UserResponse.model_validate(updated)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    summary="Deactivate/Delete user (Admin only)",
)
async def delete_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
) -> MessageResponse:
    """Soft-delete user account. Restricted to administrators."""
    await service.soft_delete_user(user_id)
    return MessageResponse(message=f"User '{user_id}' has been deactivated.")
