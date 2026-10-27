"""Unit tests for cryptographic security: Argon2id hashing and JWT validation."""

from datetime import timedelta

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    """Argon2id hashes must verify matching passwords and reject mismatched passwords."""
    raw = "SuperSecretPassword123!"
    hashed = hash_password(raw)

    assert hashed != raw
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_secure_token_generation_and_hashing() -> None:
    """Random tokens must be URL-safe and SHA-256 hashes must be deterministic 64-char strings."""
    token = generate_secure_token(32)
    assert len(token) >= 32

    hash1 = hash_token(token)
    hash2 = hash_token(token)
    assert len(hash1) == 64
    assert hash1 == hash2


def test_jwt_access_token_creation_and_decoding() -> None:
    """JWT tokens must encode claims and decode properly."""
    sub = "12345678-1234-5678-1234-567812345678"
    roles = ["user", "admin"]
    token = create_access_token(subject=sub, roles=roles)

    payload = decode_access_token(token)
    assert payload["sub"] == sub
    assert payload["roles"] == roles
    assert "exp" in payload
    assert "iss" in payload


def test_jwt_expired_token_rejection() -> None:
    """Expired JWT tokens must raise AuthenticationError."""
    sub = "12345678-1234-5678-1234-567812345678"
    token = create_access_token(subject=sub, roles=["user"], expires_delta=timedelta(seconds=-10))

    with pytest.raises(AuthenticationError, match="Token has expired"):
        decode_access_token(token)


def test_jwt_tampered_token_rejection() -> None:
    """Tampered JWT tokens must raise AuthenticationError."""
    token = create_access_token(subject="user1", roles=["user"])
    tampered = token[:-5] + "abcde"

    with pytest.raises(AuthenticationError):
        decode_access_token(tampered)
