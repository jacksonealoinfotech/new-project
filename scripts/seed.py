"""Seed initial administrator user for development and testing environments."""

import asyncio
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.common.enums import UserRole
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine, get_session_factory
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserAdminCreate
from app.modules.users.service import UserService

logger = get_logger("seed")


async def seed_admin(
    email: str = "admin@example.com",
    password: str = "AdminPassword123!",  # noqa: S107
    full_name: str = "Initial Administrator",
) -> None:
    """Create initial administrator user if one does not already exist."""
    configure_logging()
    factory = get_session_factory()

    async with factory() as session:
        user_repo = UserRepository(session)
        existing = await user_repo.get_by_email(email)
        if existing:
            logger.info("admin_already_exists", email=email)
            return

        service = UserService(session)
        created = await service.create_admin_user(
            UserAdminCreate(
                email=email,
                password=password,
                full_name=full_name,
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
        )
        logger.info("admin_seeded_successfully", user_id=str(created.id), email=email)

    await dispose_engine()


if __name__ == "__main__":
    email_arg = sys.argv[1] if len(sys.argv) > 1 else "admin@example.com"
    pass_arg = sys.argv[2] if len(sys.argv) > 2 else "AdminPassword123!"
    asyncio.run(seed_admin(email=email_arg, password=pass_arg))
