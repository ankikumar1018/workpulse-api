"""Organization repository."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from core.repository import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization model."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with session."""
        super().__init__(session, Organization)

    async def find_by_slug(self, slug: str) -> Organization | None:
        """Find organization by slug."""
        return await self.find_one(slug=slug)

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Organization], int]:
        """List organizations by status."""
        return await self.find_all(limit=limit, offset=offset, status=status)


__all__ = ["OrganizationRepository"]
