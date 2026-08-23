"""Worker persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Worker
from core.repository import BaseRepository


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
    ) -> tuple[list[Worker], int]:
        """List workers in an organization-scoped department."""
        filters: dict[str, object] = {
            "department_id": department_id,
            "organization_id": organization_id,
        }
        if status:
            filters["status"] = status
        return await self.find_all(limit=limit, offset=offset, **filters)


__all__ = ["WorkerRepository"]
