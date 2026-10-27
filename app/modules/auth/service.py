"""Authentication service managing login, registration, token rotation, and breach detection."""

from app.common.utils import utc_now
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.core.security import hash_password, hash_token, verify_password
from app.db.transaction import in_transaction
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.auth.tokens import create_user_tokens
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserResponse

logger = get_logger("auth_service")


class AuthService:
    """Coordinates authentication protocols and refresh token rotation."""

    def __init__(self, auth_repo: AuthRepository, user_repo: UserRepository) -> None:
        self.auth_repo = auth_repo
        self.user_repo = user_repo

    async def register(self, data: RegisterRequest) -> tuple[UserResponse, TokenResponse]:
        """Register a new user account and issue an initial token pair."""
        from app.modules.users.service import UserService

        user_service = UserService(self.user_repo.session)
        user = await user_service.create_user(
            UserCreate(email=data.email, password=data.password, full_name=data.full_name)
        )

        async with in_transaction(self.auth_repo.session):
            token_resp, refresh_model, _ = create_user_tokens(user)
            await self.auth_repo.create(refresh_model)

        return UserResponse.model_validate(user), token_resp

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue token pair."""
        user = await self.user_repo.get_by_email(data.email)
        # Use generic error message to prevent account enumeration
        if not user or not verify_password(data.password, user.hashed_password):
            logger.info("login_failed_invalid_credentials", email=data.email)
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            logger.warning("login_rejected_inactive_user", user_id=str(user.id))
            raise AuthenticationError("User account is inactive.")

        async with in_transaction(self.auth_repo.session):
            token_resp, refresh_model, _ = create_user_tokens(user)
            await self.auth_repo.create(refresh_model)
            logger.info("user_login_successful", user_id=str(user.id))
            return token_resp

    async def refresh_tokens(self, data: RefreshTokenRequest) -> TokenResponse:
        """Rotate refresh token. Detects token reuse and terminates affected token family."""
        token_hash = hash_token(data.refresh_token)
        stored_token = await self.auth_repo.get_by_hash(token_hash)

        if not stored_token:
            logger.warning("refresh_failed_token_not_found")
            raise AuthenticationError("Invalid refresh token.")

        # Breach detection: if a revoked token is presented, compromise is suspected
        if stored_token.is_revoked:
            logger.error(
                "refresh_token_reuse_detected",
                user_id=str(stored_token.user_id),
                family_id=str(stored_token.family_id),
            )
            async with in_transaction(self.auth_repo.session):
                await self.auth_repo.revoke_family(stored_token.family_id)
            raise AuthenticationError(
                "Invalid refresh token. Security compromise detected: session family terminated."
            )

        from datetime import UTC

        token_expires = (
            stored_token.expires_at.replace(tzinfo=UTC)
            if stored_token.expires_at.tzinfo is None
            else stored_token.expires_at
        )
        if token_expires < utc_now():
            async with in_transaction(self.auth_repo.session):
                stored_token.is_revoked = True
            logger.info("refresh_failed_token_expired", user_id=str(stored_token.user_id))
            raise AuthenticationError("Refresh token has expired.")

        user = await self.user_repo.get(stored_token.user_id)
        if not user or not user.is_active or user.is_deleted:
            raise AuthenticationError("User account is no longer active.")

        async with in_transaction(self.auth_repo.session):
            # Revoke current token upon use (rotation)
            stored_token.is_revoked = True
            # Issue new tokens preserving the family ID
            token_resp, new_refresh_model, _ = create_user_tokens(
                user, existing_family_id=stored_token.family_id
            )
            await self.auth_repo.create(new_refresh_model)
            logger.info("token_rotated_successfully", user_id=str(user.id))
            return token_resp

    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke a refresh token on logout."""
        token_hash = hash_token(raw_refresh_token)
        token = await self.auth_repo.get_by_hash(token_hash)
        if token and not token.is_revoked:
            async with in_transaction(self.auth_repo.session):
                token.is_revoked = True
            logger.info("user_logged_out", user_id=str(token.user_id))

    async def change_password(self, user: User, data: PasswordChangeRequest) -> None:
        """Verify existing password, apply new password, and revoke all active refresh tokens."""
        if not verify_password(data.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect.")

        async with in_transaction(self.user_repo.session):
            user.hashed_password = hash_password(data.new_password)
            user.version += 1
            # Revoke all existing refresh tokens
            await self.auth_repo.revoke_user_tokens(user.id)
            logger.info("password_changed_and_sessions_revoked", user_id=str(user.id))
