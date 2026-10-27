"""Pydantic schemas for User domain."""

from pydantic import EmailStr, Field

from app.common.enums import UserRole
from app.common.schemas import BaseSchema, IDSchema, TimestampSchema


class UserBase(BaseSchema):
    """Shared user attributes."""

    email: EmailStr = Field(description="User primary email address")
    full_name: str = Field(min_length=1, max_length=255, description="Full name of user")


class UserCreate(UserBase):
    """Public registration request schema. Role and administrative flags cannot be mass-assigned."""

    password: str = Field(min_length=8, max_length=128, description="Plaintext user password")


class UserUpdate(BaseSchema):
    """Self-service profile update schema."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class UserAdminCreate(UserCreate):
    """Administrative user creation schema allowing privileged role assignments."""

    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)


class UserAdminUpdate(BaseSchema):
    """Administrative user modification schema."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    is_verified: bool | None = Field(default=None)


class UserResponse(IDSchema, TimestampSchema, UserBase):
    """Public user response schema. Never exposes password hashes or security secrets."""

    role: UserRole
    is_active: bool
    is_verified: bool
    version: int


class UserFilterParams(BaseSchema):
    """Filtering criteria for administrative user search and listings."""

    role: UserRole | None = None
    is_active: bool | None = None
    search: str | None = Field(default=None, description="Search term matching email or full name")
