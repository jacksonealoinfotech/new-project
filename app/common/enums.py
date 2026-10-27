"""Domain-wide enumerations."""

from enum import StrEnum


class UserRole(StrEnum):
    """User access control roles."""

    USER = "user"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class TokenType(StrEnum):
    """JWT and session token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class OutboxStatus(StrEnum):
    """Transactional outbox message delivery status."""

    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
