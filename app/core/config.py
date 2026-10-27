"""Centralized typed application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import Environment


class Settings(BaseSettings):
    """Production application settings with strict validation and environment separation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application Metadata ---
    APP_NAME: str = Field(default="FastAPI Production Starter", description="Application name")
    APP_ENV: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application execution environment"
    )
    APP_DEBUG: bool = Field(default=False, description="Debug mode flag")
    APP_HOST: str = Field(default="0.0.0.0", description="Bind host")
    APP_PORT: int = Field(default=8000, description="Bind port")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 route prefix")
    SECRET_KEY: str = Field(
        default="development-insecure-secret-key-32-chars-minimum-length-for-testing",
        min_length=32,
        description="Core encryption secret key",
    )

    # --- Security & CORS ---
    ALLOWED_CORS_ORIGINS: list[str] | str = Field(
        default=["*"], description="Allowed CORS origin domains"
    )
    ALLOWED_HOSTS: list[str] | str = Field(default=["*"], description="Allowed host headers")

    # --- Database Settings ---
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        description="SQLAlchemy async connection URL",
    )
    DATABASE_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    DATABASE_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DATABASE_POOL_RECYCLE: int = Field(default=1800, ge=60)
    DATABASE_ECHO: bool = Field(default=False)

    # --- Redis Settings ---
    REDIS_ENABLED: bool = Field(default=False)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=1)
    REDIS_DEFAULT_TTL: int = Field(default=300, ge=1)

    # --- Authentication & JWT ---
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_SECRET_KEY: str = Field(
        default="development-insecure-jwt-secret-key-minimum-32-characters-needed",
        min_length=32,
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)
    JWT_ISSUER: str = Field(default="fastapi-production-template")
    JWT_AUDIENCE: str = Field(default="fastapi-production-template-users")

    # --- Rate Limiting ---
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_DEFAULT_REQUESTS: int = Field(default=100, ge=1)
    RATE_LIMIT_DEFAULT_WINDOW_SECONDS: int = Field(default=60, ge=1)
    RATE_LIMIT_AUTH_REQUESTS: int = Field(default=10, ge=1)
    RATE_LIMIT_AUTH_WINDOW_SECONDS: int = Field(default=60, ge=1)

    # --- Idempotency ---
    IDEMPOTENCY_EXPIRE_SECONDS: int = Field(default=86400, ge=60)

    # --- Logging & Observability ---
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="console")

    # --- Outbox & Jobs ---
    OUTBOX_ENABLED: bool = Field(default=True)
    OUTBOX_POLL_INTERVAL_SECONDS: int = Field(default=5, ge=1)
    EMAIL_BACKEND: str = Field(default="console")

    @field_validator("ALLOWED_CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_string_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if not v.strip():
                return []
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        allowed = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in allowed:
            raise ValueError(f"Unsupported JWT algorithm '{v}'. Must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Fail fast if insecure defaults are detected in production."""
        if self.APP_ENV.is_production:
            if "insecure" in self.SECRET_KEY.lower() or "development" in self.SECRET_KEY.lower():
                raise ValueError("SECRET_KEY must be a cryptographically secure key in production.")
            if (
                "insecure" in self.JWT_SECRET_KEY.lower()
                or "development" in self.JWT_SECRET_KEY.lower()
            ):
                raise ValueError(
                    "JWT_SECRET_KEY must be a cryptographically secure key in production."
                )
            if self.APP_DEBUG:
                raise ValueError("APP_DEBUG must be False in production.")
            if "*" in self.ALLOWED_CORS_ORIGINS:
                raise ValueError("Wildcard CORS origins are prohibited in production.")
            if "*" in self.ALLOWED_HOSTS:
                raise ValueError("Wildcard ALLOWED_HOSTS are prohibited in production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
