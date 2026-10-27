"""Authentication request and response schemas."""

from pydantic import EmailStr, Field

from app.common.schemas import BaseSchema


class LoginRequest(BaseSchema):
    """Credentials payload for obtaining authentication tokens."""

    email: EmailStr = Field(description="Account email address")
    password: str = Field(min_length=1, description="Account password")


class RegisterRequest(BaseSchema):
    """Payload for self-service user registration."""

    email: EmailStr = Field(description="Account email address")
    password: str = Field(min_length=8, max_length=128, description="Account password")
    full_name: str = Field(min_length=1, max_length=255, description="Full name of user")


class TokenResponse(BaseSchema):
    """Token response returned upon successful login or refresh."""

    access_token: str = Field(description="Short-lived JWT access token")
    refresh_token: str = Field(description="Rotatable opaque refresh token")
    token_type: str = Field(default="bearer", description="Token scheme")
    expires_in: int = Field(description="Access token lifespan in seconds")


class RefreshTokenRequest(BaseSchema):
    """Payload for rotating refresh token and receiving a new access token."""

    refresh_token: str = Field(description="Valid non-revoked opaque refresh token")


class PasswordChangeRequest(BaseSchema):
    """Payload for changing current user's password."""

    current_password: str = Field(min_length=1, description="Current account password")
    new_password: str = Field(min_length=8, max_length=128, description="New password")
