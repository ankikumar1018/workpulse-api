"""Logical communication job lifecycle service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.communication_job import (
    CommunicationJob as CommunicationJobDomain,
    InvalidCommunicationJobTransitionError,
)
from app.domain.enums import Channel, CommunicationJobStatus
from app.domain.idempotency import build_communication_job_key
from app.infrastructure.db.models import CommunicationJob
from app.repositories.communication_job import (
    CommunicationJobHistoryRepository,
    CommunicationJobRepository,
)


class CommunicationJobService:
    """Persist and transition logical jobs independently from message delivery."""

    def __init__(
        self,
        repository: CommunicationJobRepository,
        history_repository: CommunicationJobHistoryRepository | None = None,
    ):
        self.repository = repository
        self.history_repository = history_repository

    async def get_job(self, *, job_id: UUID, organization_id: UUID) -> CommunicationJob:
        job = await self.repository.get_in_organization(
            job_id=job_id, organization_id=organization_id
        )
        if job is None:
            raise NotFoundError(f"Communication job '{job_id}' not found")
        return job

    async def list_jobs(
        self,
        *,
        organization_id: UUID,
        status: CommunicationJobStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[CommunicationJob], int]:
        return await self.repository.list_in_organization(
            organization_id=organization_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def create_job(
        self,
        *,
        organization_id: UUID,
        schedule_id: UUID,
        template_id: UUID,
        work_item_id: UUID | None,
        worker_id: UUID,
        channel: Channel,
        execution_at: datetime,
    ) -> CommunicationJob:
        if execution_at.tzinfo is None:
            raise UnprocessableEntityError("Job execution time must include timezone information")
        job_key = build_communication_job_key(
            organization_id=organization_id,
            schedule_id=schedule_id,
            template_id=template_id,
            worker_id=worker_id,
            execution_at=execution_at,
        )
        return await self.repository.create_idempotent(
            {
                "organization_id": organization_id,
                "schedule_id": schedule_id,
                "template_id": template_id,
                "work_item_id": work_item_id,
                "worker_id": worker_id,
                "channel": channel,
                "execution_at": execution_at,
                "job_key": job_key,
                "status": CommunicationJobStatus.PENDING,
            }
        )

    async def transition_job(
        self,
        *,
        job_id: UUID,
        organization_id: UUID,
        new_status: CommunicationJobStatus,
        reason_code: str | None = None,
        reason: str | None = None,
        queue_reference: str | None = None,
        occurred_at: datetime | None = None,
    ) -> CommunicationJob:
        job = await self.get_job(job_id=job_id, organization_id=organization_id)
        previous_status = job.status
        domain_job = CommunicationJobDomain(
            id=job.id,
            organization_id=job.organization_id,
            job_key=job.job_key,
            status=job.status,
            attempt_count=job.attempt_count,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        try:
            domain_job.transition_to(new_status)
        except InvalidCommunicationJobTransitionError as error:
            raise UnprocessableEntityError(str(error)) from error

        occurred_at = occurred_at or datetime.now(UTC)
        job.status = new_status
        if new_status == CommunicationJobStatus.PROCESSING:
            job.attempt_count = (job.attempt_count or 0) + 1
            job.started_at = occurred_at
        if new_status in {
            CommunicationJobStatus.COMPLETED,
            CommunicationJobStatus.CANCELLED,
            CommunicationJobStatus.SUPPRESSED,
        }:
            job.completed_at = occurred_at
        if new_status == CommunicationJobStatus.FAILED:
            job.last_error_code = reason_code
            job.last_error_message = reason
        if self.history_repository is None:
            await self.repository.session.commit()
            await self.repository.session.refresh(job)
        else:
            await self.repository.save_transition(
                job=job,
                previous_status=previous_status,
                new_status=new_status,
                reason_code=reason_code,
                reason=reason,
                queue_reference=queue_reference,
                occurred_at=occurred_at,
            )
        return job

    async def list_history(self, *, job_id: UUID, organization_id: UUID) -> list:
        await self.get_job(job_id=job_id, organization_id=organization_id)
        if self.history_repository is None:
            return []
        return await self.history_repository.list_for_job(
            job_id=job_id, organization_id=organization_id
        )


__all__ = ["CommunicationJobService"]
