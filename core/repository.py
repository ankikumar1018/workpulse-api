"""Base repository pattern for all repositories."""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository[T]:
    """
    Base repository class for all models.

    Provides common CRUD operations and query builders.
    All repositories should inherit from this class and override
    the model class variable.
    """

    def __init__(self, session: AsyncSession, model: type[T]):
        """Initialize repository with session and model."""
        self.session = session
        self.model = model

    async def create(self, obj_in: dict[str, Any] | T) -> T:
        """Create a new record."""
        obj = self.model(**obj_in) if isinstance(obj_in, dict) else obj_in

        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, obj_id: Any) -> T | None:
        """Get record by ID."""
        return await self.session.get(self.model, obj_id)

    async def find_one(self, **filters: Any) -> T | None:
        """Find one record matching filters."""
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalars().first()

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters: Any,
    ) -> tuple[list[T], int]:
        """Find all records matching filters with pagination."""
        # Build query
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)

        # Get total count
        count_query = select(func.count(self.model.id)).select_from(self.model)
        for key, value in filters.items():
            count_query = count_query.where(getattr(self.model, key) == value)

        count_result = await self.session.execute(count_query)
        total = count_result.scalars().first() or 0

        # Get paginated results
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def update(self, obj_id: Any, obj_in: dict[str, Any]) -> T | None:
        """Update a record."""
        obj = await self.get_by_id(obj_id)
        if obj:
            for key, value in obj_in.items():
                setattr(obj, key, value)
            await self.session.commit()
            await self.session.refresh(obj)
        return obj

    async def delete(self, obj_id: Any) -> bool:
        """Delete a record."""
        obj = await self.get_by_id(obj_id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            return True
        return False


__all__ = ["BaseRepository"]
