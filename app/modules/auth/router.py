"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, status

from app.core.rate_limit import rate_limit
from app.core.responses import MessageResponse
from app.modules.auth.dependencies import get_auth_service, get_current_active_user
from app.modules.auth.schemas import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=dict[str, UserResponse | TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, UserResponse | TokenResponse]:
    """Register a new user account and obtain initial authentication tokens."""
    user, tokens = await service.register(data)
    return {"user": user, "tokens": tokens}


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
    summary="Authenticate user and receive token pair",
)
async def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Validate credentials and return JWT access token plus rotatable refresh token."""
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and get a new access token",
)
async def refresh(
    data: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token and rotated refresh token."""
    return await service.refresh_tokens(data)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke active refresh token",
)
async def logout(
    data: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Revoke the provided refresh token session."""
    await service.logout(data.refresh_token)
    return MessageResponse(message="Successfully logged out.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change user password and revoke existing sessions",
)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Update password for the authenticated user and invalidate active refresh tokens."""
    await service.change_password(current_user, data)
    return MessageResponse(message="Password successfully updated. All other sessions revoked.")
