"""Department persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Department
from core.repository import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    """Tenant-scoped department repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Department)

    async def find_by_name(self, *, project_id: UUID, name: str) -> Department | None:
        """Find a department by name within a project."""
        result = await self.session.execute(
            select(Department).where(
                Department.project_id == project_id,
                Department.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def get_in_organization(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
    ) -> Department | None:
        """Find a department without crossing the organization boundary."""
        result = await self.session.execute(
            select(Department).where(
                Department.id == department_id,
                Department.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_project(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Department], int]:
        """List departments within an organization-scoped project."""
        filters: dict[str, object] = {
            "project_id": project_id,
            "organization_id": organization_id,
        }
        if status:
            filters["status"] = status
        return await self.find_all(limit=limit, offset=offset, **filters)


__all__ = ["DepartmentRepository"]
