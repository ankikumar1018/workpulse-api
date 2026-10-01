"""Tenant-scoped communication job persistence operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import CommunicationJobStatus
from app.infrastructure.db.models import CommunicationJob, CommunicationJobStatusHistory
from app.infrastructure.repository import BaseRepository


class CommunicationJobRepository(BaseRepository[CommunicationJob]):
    """Persist logical jobs without coupling them to queue operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, CommunicationJob)

    async def get_in_organization(
        self, *, job_id: UUID, organization_id: UUID
    ) -> CommunicationJob | None:
        result = await self.session.execute(
            select(CommunicationJob).where(
                CommunicationJob.id == job_id,
                CommunicationJob.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_job_key(
        self, *, organization_id: UUID, job_key: str
    ) -> CommunicationJob | None:
        result = await self.session.execute(
            select(CommunicationJob).where(
                CommunicationJob.organization_id == organization_id,
                CommunicationJob.job_key == job_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_idempotent(self, job_data: dict[str, Any]) -> CommunicationJob:
        existing = await self.find_by_job_key(
            organization_id=job_data["organization_id"], job_key=job_data["job_key"]
        )
        if existing is not None:
            return existing
        job = CommunicationJob(**job_data)
        self.session.add(job)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.find_by_job_key(
                organization_id=job_data["organization_id"], job_key=job_data["job_key"]
            )
            if existing is not None:
                return existing
            raise
        await self.session.refresh(job)
        return job

    async def save_transition(
        self,
        *,
        job: CommunicationJob,
        previous_status: CommunicationJobStatus,
        new_status: CommunicationJobStatus,
        reason_code: str | None,
        reason: str | None,
        queue_reference: str | None,
        occurred_at: datetime,
    ) -> CommunicationJobStatusHistory:
        history = CommunicationJobStatusHistory(
            organization_id=job.organization_id,
            job_id=job.id,
            previous_status=previous_status,
            new_status=new_status,
            reason_code=reason_code,
            reason=reason,
            queue_reference=queue_reference,
            created_at=occurred_at,
        )
        self.session.add(job)
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(job)
        await self.session.refresh(history)
        return history


class CommunicationJobHistoryRepository:
    """Read-only tenant-scoped logical job history queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_job(
        self, *, job_id: UUID, organization_id: UUID
    ) -> list[CommunicationJobStatusHistory]:
        result = await self.session.execute(
            select(CommunicationJobStatusHistory)
            .where(
                CommunicationJobStatusHistory.job_id == job_id,
                CommunicationJobStatusHistory.organization_id == organization_id,
            )
            .order_by(
                CommunicationJobStatusHistory.created_at,
                CommunicationJobStatusHistory.id,
            )
        )
        return list(result.scalars().all())


__all__ = ["CommunicationJobHistoryRepository", "CommunicationJobRepository"]
