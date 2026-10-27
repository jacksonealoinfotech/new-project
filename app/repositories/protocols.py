"""Repository protocol defining generic data access interface."""

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT")


class RepositoryProtocol(Protocol[ModelT]):
    """Standard repository contract for asynchronous persistence operations."""

    async def get(self, id: Any) -> ModelT | None:
        """Fetch single record by primary key."""
        ...

    async def get_by(self, **kwargs: Any) -> ModelT | None:
        """Fetch single record matching field criteria."""
        ...

    async def list(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: Any = None,
    ) -> list[ModelT]:
        """Fetch ordered list of records matching optional filters."""
        ...

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total matching records."""
        ...

    async def create(self, instance: ModelT) -> ModelT:
        """Persist new record instance into database."""
        ...

    async def update(self, instance: ModelT, data: dict[str, Any] | BaseModel) -> ModelT:
        """Apply updates to an existing persisted instance."""
        ...

    async def delete(self, instance: ModelT) -> None:
        """Delete instance from database."""
        ...

    async def exists(self, **kwargs: Any) -> bool:
        """Check if any record matches criteria."""
        ...
