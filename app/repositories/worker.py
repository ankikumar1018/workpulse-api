"""Worker persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Worker
from app.infrastructure.repository import BaseRepository


class WorkerRepository(BaseRepository[Worker]):
    """Tenant-scoped worker repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Worker)

    async def find_by_phone(self, *, organization_id: UUID, phone_number: str) -> Worker | None:
        """Find a worker by phone number within an organization."""
        result = await self.session.execute(
            select(Worker).where(
                Worker.organization_id == organization_id,
                Worker.phone_number == phone_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_in_organization(
        self,
        *,
        worker_id: UUID,
        organization_id: UUID,
    ) -> Worker | None:
        """Find a worker without crossing the organization boundary."""
        result = await self.session.execute(
            select(Worker).where(
                Worker.id == worker_id,
                Worker.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_department(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
        consent_status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Worker], int]:
        """List workers in an organization-scoped department."""
        query = select(Worker).where(
            Worker.department_id == department_id,
            Worker.organization_id == organization_id,
        )
        count_query = select(func.count(Worker.id)).where(
            Worker.department_id == department_id,
            Worker.organization_id == organization_id,
        )
        if status:
            query = query.where(Worker.status == status)
            count_query = count_query.where(Worker.status == status)
        if consent_status:
            query = query.where(Worker.consent_status == consent_status)
            count_query = count_query.where(Worker.consent_status == consent_status)
        if search:
            pattern = f"%{search}%"
            search_filter = or_(Worker.full_name.ilike(pattern), Worker.phone_number.ilike(pattern))
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        query = query.order_by(Worker.full_name, Worker.id)
        total = await self.session.scalar(count_query) or 0
        result = await self.session.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all()), total


__all__ = ["WorkerRepository"]
