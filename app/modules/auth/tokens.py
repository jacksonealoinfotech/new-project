"""Token factory and rotation utilities."""

import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.security import create_access_token, generate_secure_token, hash_token
from app.modules.auth.models import RefreshToken
from app.modules.auth.schemas import TokenResponse
from app.modules.users.models import User


def create_user_tokens(
    user: User,
    existing_family_id: uuid.UUID | None = None,
) -> tuple[TokenResponse, RefreshToken, str]:
    """Generate a JWT access token and a rotatable refresh token pair.

    Returns (TokenResponse, RefreshToken_ORM_model, raw_refresh_token_string).
    """
    settings = get_settings()
    access_token = create_access_token(
        subject=str(user.id),
        roles=[user.role.value],
    )

    raw_refresh_token = generate_secure_token(32)
    refresh_hash = hash_token(raw_refresh_token)
    family_id = existing_family_id or uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token_model = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        family_id=family_id,
        is_revoked=False,
        expires_at=expires_at,
    )

    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return token_response, refresh_token_model, raw_refresh_token
