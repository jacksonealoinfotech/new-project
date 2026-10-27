"""Authentication repository managing refresh token persistence and revocation."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken
from app.repositories.base import BaseRepository


class AuthRepository(BaseRepository[RefreshToken]):
    """Data access repository for refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=RefreshToken, session=session)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find refresh token by SHA-256 hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def revoke_family(self, family_id: uuid.UUID) -> int:
        """Revoke all tokens in a token family upon breach / reuse detection."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, ~RefreshToken.is_revoked)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    async def revoke_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke all active tokens for a user (e.g. on password change)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, ~RefreshToken.is_revoked)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(getattr(result, "rowcount", 0) or 0)
