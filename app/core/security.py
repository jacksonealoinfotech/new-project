"""Cryptographic security utilities: Argon2id password hashing and JWT management."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

# Argon2id password hasher using default secure OWASP recommended parameters
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def generate_secure_token(length_bytes: int = 32) -> str:
    """Generate a cryptographically secure random token URL-safe string."""
    return secrets.token_urlsafe(length_bytes)


def hash_token(raw_token: str) -> str:
    """Compute a SHA-256 hash of a raw token for secure database persistence."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    roles: list[str],
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token with issuer, audience, and expiry claims."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires = (
        now + expires_delta
        if expires_delta
        else now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    import uuid

    payload: dict[str, Any] = {
        "sub": subject,
        "roles": roles,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token against allowlisted algorithms, issuer, and audience."""
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(message="Token has expired.") from None
    except jwt.InvalidTokenError as err:
        raise AuthenticationError(message=f"Invalid token: {err!s}") from None
