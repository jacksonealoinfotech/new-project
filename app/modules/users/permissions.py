"""User domain authorization policies and ownership rules."""

import uuid

from app.common.enums import UserRole
from app.core.exceptions import PermissionDeniedError
from app.modules.users.models import User


def check_can_view_user(current_user: User, target_user_id: uuid.UUID) -> None:
    """Verify that current user is an administrator or accessing their own record."""
    if current_user.role in (UserRole.ADMIN, UserRole.SUPERUSER):
        return
    if current_user.id == target_user_id:
        return
    raise PermissionDeniedError("You are not authorized to view this user account.")


def check_can_modify_user(current_user: User, target_user_id: uuid.UUID) -> None:
    """Verify that current user is an administrator or updating their own record."""
    if current_user.role in (UserRole.ADMIN, UserRole.SUPERUSER):
        return
    if current_user.id == target_user_id:
        return
    raise PermissionDeniedError("You are not authorized to modify this user account.")


def check_is_admin(current_user: User) -> None:
    """Enforce administrative role requirement."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPERUSER):
        raise PermissionDeniedError("Administrator privileges are required for this action.")
