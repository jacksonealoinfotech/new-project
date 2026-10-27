"""Unit tests for configuration validation and environment security gates."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.constants import Environment


def test_development_settings_defaults() -> None:
    """Ensure standard settings instantiate successfully under development defaults."""
    settings = Settings(
        APP_ENV=Environment.DEVELOPMENT,
        SECRET_KEY="a" * 32,
        JWT_SECRET_KEY="b" * 32,
        ALLOWED_CORS_ORIGINS=["http://localhost:3000"],
    )
    assert "FastAPI" in settings.APP_NAME
    assert not settings.APP_ENV.is_production
    assert settings.JWT_ALGORITHM == "HS256"


def test_cors_origins_comma_separated_parsing() -> None:
    """Ensure comma-separated strings are parsed into list of origins."""
    settings = Settings(
        ALLOWED_CORS_ORIGINS="http://localhost:3000, http://example.com",
        SECRET_KEY="a" * 32,
        JWT_SECRET_KEY="b" * 32,
    )
    assert settings.ALLOWED_CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]


def test_production_fails_with_insecure_secret_key() -> None:
    """Production environment must immediately reject default insecure secret keys."""
    with pytest.raises(ValidationError, match="SECRET_KEY must be a cryptographically secure key"):
        Settings(
            APP_ENV=Environment.PRODUCTION,
            APP_DEBUG=False,
            SECRET_KEY="insecure-development-secret-key-12345678",
            JWT_SECRET_KEY="a" * 32,
            ALLOWED_CORS_ORIGINS=["https://app.example.com"],
            ALLOWED_HOSTS=["api.example.com"],
        )


def test_production_fails_with_wildcard_cors() -> None:
    """Production environment must reject wildcard CORS."""
    with pytest.raises(ValidationError, match="Wildcard CORS origins are prohibited"):
        Settings(
            APP_ENV=Environment.PRODUCTION,
            APP_DEBUG=False,
            SECRET_KEY="production-secure-key-with-sufficient-entropy-123",
            JWT_SECRET_KEY="production-jwt-key-with-sufficient-entropy-123",
            ALLOWED_CORS_ORIGINS=["*"],
            ALLOWED_HOSTS=["api.example.com"],
        )


def test_jwt_algorithm_whitelist() -> None:
    """Only approved signing algorithms should be accepted."""
    with pytest.raises(ValidationError, match="Unsupported JWT algorithm"):
        Settings(
            JWT_ALGORITHM="none",
            SECRET_KEY="a" * 32,
            JWT_SECRET_KEY="b" * 32,
        )
