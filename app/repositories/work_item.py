"""Work item persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import WorkItem
from app.infrastructure.repository import BaseRepository


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
        priority: str | None = None,
        overdue: bool | None = None,
    ) -> tuple[list[WorkItem], int]:
        """List work items in an organization-scoped project."""
        query = select(WorkItem).where(
            WorkItem.project_id == project_id,
            WorkItem.organization_id == organization_id,
        )
        count_query = select(func.count(WorkItem.id)).where(
            WorkItem.project_id == project_id,
            WorkItem.organization_id == organization_id,
        )

        if department_id:
            query = query.where(WorkItem.department_id == department_id)
            count_query = count_query.where(WorkItem.department_id == department_id)
        if status:
            query = query.where(WorkItem.status == status)
            count_query = count_query.where(WorkItem.status == status)
        if priority:
            query = query.where(WorkItem.priority == priority)
            count_query = count_query.where(WorkItem.priority == priority)
        if overdue is not None:
            if overdue:
                query = query.where(WorkItem.due_at.is_not(None), WorkItem.due_at < func.now())
                count_query = count_query.where(
                    WorkItem.due_at.is_not(None), WorkItem.due_at < func.now()
                )
            else:
                query = query.where(WorkItem.due_at.is_(None) | (WorkItem.due_at >= func.now()))
                count_query = count_query.where(
                    WorkItem.due_at.is_(None) | (WorkItem.due_at >= func.now())
                )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one() or 0
        result = await self.session.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all()), total

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
