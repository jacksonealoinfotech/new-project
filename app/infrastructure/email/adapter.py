"""Email notification adapter protocol and development implementation."""

from typing import Protocol

from app.core.logging import get_logger

logger = get_logger("email_adapter")


class EmailAdapter(Protocol):
    """Protocol defining transactional email delivery operations."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool: ...


class ConsoleEmailAdapter:
    """Console email adapter for development and testing environments."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        logger.info(
            "dispatching_email_via_console",
            to_email=to_email,
            subject=subject,
            preview=text_body[:100] if text_body else html_body[:100],
        )
        return True


def get_email_adapter() -> EmailAdapter:
    """Factory retrieving configured email adapter."""
    return ConsoleEmailAdapter()
