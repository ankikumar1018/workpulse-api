"""Work item persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import WorkItem
from core.repository import BaseRepository


class WorkItemRepository(BaseRepository[WorkItem]):
    """Tenant-scoped work item repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, WorkItem)

    async def get_in_project(
        self,
        *,
        work_item_id: UUID,
        organization_id: UUID,
        project_id: UUID,
    ) -> WorkItem | None:
        """Find a work item within an organization and project scope.

        Args:
            work_item_id: Work item ID
            organization_id: Organization ID
            project_id: Project ID

        Returns:
            The work item if found and scoped correctly, None otherwise
        """
        result = await self.session.execute(
            select(WorkItem).where(
                WorkItem.id == work_item_id,
                WorkItem.organization_id == organization_id,
                WorkItem.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_in_organization(
        self,
        *,
        work_item_id: UUID,
        organization_id: UUID,
    ) -> WorkItem | None:
        """Find a work item within an organization scope.

        Args:
            work_item_id: Work item ID
            organization_id: Organization ID

        Returns:
            The work item if found and scoped correctly, None otherwise
        """
        result = await self.session.execute(
            select(WorkItem).where(
                WorkItem.id == work_item_id,
                WorkItem.organization_id == organization_id,
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
        department_id: UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[WorkItem], int]:
        """List work items in an organization-scoped project.

        Args:
            project_id: Project ID
            organization_id: Organization ID
            limit: Number of items to return
            offset: Number of items to skip
            department_id: Optional filter by department
            status: Optional filter by status

        Returns:
            Tuple of (list of work items, total count)
        """
        filters: dict[str, object] = {
            "project_id": project_id,
            "organization_id": organization_id,
        }
        if department_id:
            filters["department_id"] = department_id
        if status:
            filters["status"] = status
        return await self.find_all(limit=limit, offset=offset, **filters)

    async def list_in_department(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[WorkItem], int]:
        """List work items in an organization-scoped department.

        Args:
            department_id: Department ID
            organization_id: Organization ID
            limit: Number of items to return
            offset: Number of items to skip
            status: Optional filter by status

        Returns:
            Tuple of (list of work items, total count)
        """
        filters: dict[str, object] = {
            "department_id": department_id,
            "organization_id": organization_id,
        }
        if status:
            filters["status"] = status
        return await self.find_all(limit=limit, offset=offset, **filters)


__all__ = ["WorkItemRepository"]
