"""User domain specific exceptions."""

import uuid

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError


class UserNotFoundError(ResourceNotFoundError):
    """Raised when requested user cannot be found."""

    def __init__(self, identifier: uuid.UUID | str) -> None:
        super().__init__(resource="User", identifier=identifier)


class UserAlreadyExistsError(ResourceConflictError):
    """Raised when attempting to create a user with an already registered email."""

    def __init__(self, email: str) -> None:
        super().__init__(message=f"User with email '{email}' already exists.")
