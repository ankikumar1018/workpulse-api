"""Project persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Project
from core.repository import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Tenant-scoped project repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Project)

    async def find_by_name(self, *, organization_id: UUID, name: str) -> Project | None:
        """Find a project by name within an organization."""
        result = await self.session.execute(
            select(Project).where(
                Project.organization_id == organization_id,
                Project.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def get_in_organization(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
    ) -> Project | None:
        """Find a project without crossing the organization boundary."""
        result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_organization(
        self,
        *,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Project], int]:
        """List projects belonging to one organization."""
        filters: dict[str, object] = {"organization_id": organization_id}
        if status:
            filters["status"] = status
        return await self.find_all(limit=limit, offset=offset, **filters)


__all__ = ["ProjectRepository"]
