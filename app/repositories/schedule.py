"""Schedule persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Schedule
from app.infrastructure.repository import BaseRepository


class ScheduleRepository(BaseRepository[Schedule]):
    """Tenant-scoped schedule queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Schedule)

    async def get_in_organization(
        self,
        *,
        schedule_id: UUID,
        organization_id: UUID,
    ) -> Schedule | None:
        result = await self.session.execute(
            select(Schedule).where(
                Schedule.id == schedule_id,
                Schedule.organization_id == organization_id,
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
    ) -> tuple[list[Schedule], int]:
        filters: dict[str, object] = {
            "project_id": project_id,
            "organization_id": organization_id,
        }
        if status:
            filters["status"] = status
        return await self.find_all(limit=limit, offset=offset, **filters)


__all__ = ["ScheduleRepository"]
