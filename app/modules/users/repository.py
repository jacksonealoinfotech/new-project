"""User database repository implementing domain-specific queries."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.schemas import UserFilterParams
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access repository for User entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=User, session=session)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by case-insensitive email address."""
        stmt = select(User).where(func.lower(User.email) == email.lower(), ~User.is_deleted)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_filtered(
        self,
        offset: int,
        limit: int,
        filters: UserFilterParams | None = None,
    ) -> tuple[list[User], int]:
        """Fetch filtered and paginated user list along with total count."""
        query = select(User).where(~User.is_deleted)
        count_query = select(func.count()).select_from(User).where(~User.is_deleted)

        if filters:
            conditions = []
            if filters.role is not None:
                conditions.append(User.role == filters.role)
            if filters.is_active is not None:
                conditions.append(User.is_active == filters.is_active)
            if filters.search:
                search_term = f"%{filters.search.lower()}%"
                conditions.append(
                    or_(
                        func.lower(User.email).like(search_term),
                        func.lower(User.full_name).like(search_term),
                    )
                )

            for cond in conditions:
                query = query.where(cond)
                count_query = count_query.where(cond)

        # Order deterministically by created_at desc, id desc
        query = query.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit)

        records_res = await self.session.execute(query)
        total_res = await self.session.execute(count_query)

        items = list(records_res.scalars().all())
        total = total_res.scalar_one_or_none() or 0
        return items, total
