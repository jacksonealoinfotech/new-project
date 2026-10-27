"""Reusable SQLAlchemy 2.x generic repository implementation."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT", bound=Any)


class BaseRepository(Generic[ModelT]):
    """Generic asynchronous repository providing type-safe CRUD without hidden commits."""

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, id: Any) -> ModelT | None:
        """Fetch entity by primary key."""
        return await self.session.get(self.model, id)

    async def get_by(self, **kwargs: Any) -> ModelT | None:
        """Fetch first entity matching field keyword filters."""
        stmt = select(self.model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: Any = None,
    ) -> list[ModelT]:
        """Fetch paginated entities with optional filters and ordering."""
        stmt = select(self.model)
        if filters:
            for field, val in filters.items():
                if val is not None and hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == val)

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total matching entities."""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            for field, val in filters.items():
                if val is not None and hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == val)
        result = await self.session.execute(stmt)
        count_val = result.scalar_one_or_none()
        return count_val or 0

    async def create(self, instance: ModelT) -> ModelT:
        """Add new entity instance to session and flush to generate primary keys."""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelT, data: dict[str, Any] | BaseModel) -> ModelT:
        """Update entity attributes and flush changes."""
        update_dict = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete entity from persistence and flush."""
        await self.session.delete(instance)
        await self.session.flush()

    async def exists(self, **kwargs: Any) -> bool:
        """Check if at least one entity matches criteria."""
        stmt = select(func.count()).select_from(self.model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        count_val = result.scalar_one_or_none()
        return bool(count_val and count_val > 0)
