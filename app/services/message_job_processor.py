"""Execute logical communication jobs against fresh application state."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date
from typing import Any
from uuid import UUID

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.enums import (
    CommunicationJobStatus,
    ConsentStatus,
    DeliveryStatus,
    EntityStatus,
    ScheduleStatus,
    WorkerStatus,
    WorkStatus,
)
from app.domain.message_provider import OutboundMessageProvider
from app.domain.template import TemplateRenderContext


@dataclass(frozen=True)
class MessageJobResult:
    """Provider-neutral outcome of one processor invocation."""

    job_status: CommunicationJobStatus
    message_id: UUID | None = None
    reason_code: str | None = None


class MessageJobProcessor:
    """Revalidate, render and dispatch one logical communication job."""

    def __init__(
        self,
        *,
        job_service: Any,
        message_service: Any,
        schedule_repository: Any,
        project_repository: Any,
        department_repository: Any,
        worker_repository: Any,
        work_item_repository: Any,
        template_service: Any,
        rate_limiter: Any | None = None,
        max_attempts: int = 3,
        retry_classifier: Callable[[str | None], bool] | None = None,
    ) -> None:
        self.job_service = job_service
        self.message_service = message_service
        self.schedule_repository = schedule_repository
        self.project_repository = project_repository
        self.department_repository = department_repository
        self.worker_repository = worker_repository
        self.work_item_repository = work_item_repository
        self.template_service = template_service
        self.rate_limiter = rate_limiter
        self.max_attempts = max_attempts
        self.retry_classifier = retry_classifier or self._is_retryable_error
        self._execution_locks: dict[tuple[UUID, UUID], asyncio.Lock] = {}

    async def process(
        self,
        *,
        job_id: UUID,
        organization_id: UUID,
        provider: OutboundMessageProvider,
    ) -> MessageJobResult:
        """Process a job once, rejecting concurrent duplicate deliveries."""
        key = (organization_id, job_id)
        lock = self._execution_locks.setdefault(key, asyncio.Lock())
        if lock.locked():
            return MessageJobResult(
                job_status=CommunicationJobStatus.PROCESSING,
                reason_code="DUPLICATE_IN_FLIGHT",
            )
        async with lock:
            return await self._process_once(
                job_id=job_id,
                organization_id=organization_id,
                provider=provider,
            )

    async def _process_once(
        self,
        *,
        job_id: UUID,
        organization_id: UUID,
        provider: OutboundMessageProvider,
    ) -> MessageJobResult:
        """Process a job using the selected channel provider."""
        job = await self.job_service.get_job(job_id=job_id, organization_id=organization_id)
        if job.status in {
            CommunicationJobStatus.COMPLETED,
            CommunicationJobStatus.CANCELLED,
            CommunicationJobStatus.SUPPRESSED,
            CommunicationJobStatus.PROCESSING,
        }:
            return MessageJobResult(job_status=job.status)
        if job.attempt_count >= self.max_attempts:
            return MessageJobResult(
                job_status=CommunicationJobStatus.FAILED,
                reason_code="MAX_ATTEMPTS_EXCEEDED",
            )

        schedule = await self._get_or_suppress(
            self.schedule_repository,
            "get_in_organization",
            schedule_id=job.schedule_id,
            organization_id=organization_id,
        )
        if schedule is None:
            return MessageJobResult(
                CommunicationJobStatus.SUPPRESSED, reason_code="SCHEDULE_NOT_FOUND"
            )
        if schedule.status != ScheduleStatus.ACTIVE:
            return await self._suppress(
                job, "SCHEDULE_INACTIVE", "The schedule is no longer active."
            )

        project = await self._get_or_suppress(
            self.project_repository,
            "get_in_organization",
            project_id=schedule.project_id,
            organization_id=organization_id,
        )
        if project is None:
            return MessageJobResult(
                CommunicationJobStatus.SUPPRESSED, reason_code="PROJECT_NOT_FOUND"
            )
        if project.status == EntityStatus.ARCHIVED:
            return await self._suppress(job, "PROJECT_INACTIVE", "The project is archived.")

        department = await self._get_or_suppress(
            self.department_repository,
            "get_in_organization",
            department_id=schedule.department_id,
            organization_id=organization_id,
        )
        if department is None:
            return MessageJobResult(
                CommunicationJobStatus.SUPPRESSED, reason_code="DEPARTMENT_NOT_FOUND"
            )

        worker = await self._get_or_suppress(
            self.worker_repository,
            "get_in_organization",
            worker_id=job.worker_id,
            organization_id=organization_id,
        )
        if worker is None:
            return MessageJobResult(
                CommunicationJobStatus.SUPPRESSED, reason_code="WORKER_NOT_FOUND"
            )
        if worker.status != WorkerStatus.ACTIVE:
            return await self._suppress(job, "WORKER_INACTIVE", "The worker is not active.")
        if worker.consent_status != ConsentStatus.OPTED_IN:
            return await self._suppress(job, "CONSENT_REQUIRED", "The worker has not opted in.")
        if worker.contact_channel != job.channel:
            return await self._suppress(
                job, "CHANNEL_UNAVAILABLE", "The worker channel does not match the job."
            )

        work_item = None
        if job.work_item_id is not None:
            work_item = await self.work_item_repository.get_in_organization(
                work_item_id=job.work_item_id,
                organization_id=organization_id,
            )
            if work_item is None:
                return await self._suppress(
                    job, "WORK_ITEM_NOT_FOUND", "The configured work item no longer exists."
                )
            if work_item.status in {WorkStatus.DONE, WorkStatus.CANCELLED}:
                return await self._suppress(
                    job, "WORK_ITEM_CLOSED", "The work item is already closed."
                )

        try:
            template = await self.template_service.get_template(
                template_id=job.template_id,
                organization_id=organization_id,
            )
        except NotFoundError, UnprocessableEntityError:
            return await self._suppress(
                job, "TEMPLATE_UNAVAILABLE", "The configured template is unavailable."
            )
        if template.channel != job.channel or template.status == EntityStatus.ARCHIVED:
            return await self._suppress(
                job, "TEMPLATE_UNAVAILABLE", "The configured template is unavailable."
            )

        try:
            rendered_body = await self.template_service.render_template(
                template_id=job.template_id,
                organization_id=organization_id,
                context=TemplateRenderContext(
                    project_name=project.name,
                    department_name=department.name,
                    current_date=job.execution_at.astimezone(UTC).date(),
                    work_status=work_item.status.value if work_item else "none",
                    primary_contact_name=worker.full_name,
                    work_item_title=work_item.title if work_item else None,
                    priority=work_item.priority.value if work_item else None,
                    due_date=self._due_date(work_item),
                ),
            )
        except NotFoundError, UnprocessableEntityError:
            return await self._suppress(
                job, "TEMPLATE_UNAVAILABLE", "The configured template could not be rendered."
            )
        message = await self.message_service.create_message(
            organization_id=organization_id,
            schedule_id=job.schedule_id,
            template_id=job.template_id,
            work_item_id=job.work_item_id,
            worker_id=job.worker_id,
            channel=job.channel,
            recipient_phone_number=worker.phone_number,
            rendered_body=rendered_body,
            execution_at=job.execution_at,
        )
        if message.delivery_status in {DeliveryStatus.SENT, DeliveryStatus.DELIVERED}:
            await self.job_service.transition_job(
                job_id=job.id,
                organization_id=organization_id,
                new_status=CommunicationJobStatus.COMPLETED,
            )
            return MessageJobResult(CommunicationJobStatus.COMPLETED, message.id)
        if message.delivery_status == DeliveryStatus.FAILED and not self.retry_classifier(
            message.error_code
        ):
            return await self._fail_existing_message(job, message)
        if message.delivery_status not in {DeliveryStatus.QUEUED, DeliveryStatus.FAILED}:
            return await self._fail_existing_message(job, message)

        if self.rate_limiter is not None:
            await self.rate_limiter.acquire(channel=job.channel)
        await self.job_service.transition_job(
            job_id=job.id,
            organization_id=organization_id,
            new_status=CommunicationJobStatus.PROCESSING,
        )
        dispatched = await self.message_service.dispatch_message(
            message_id=message.id,
            organization_id=organization_id,
            provider=provider,
        )
        if dispatched.delivery_status in {DeliveryStatus.SENT, DeliveryStatus.DELIVERED}:
            await self.job_service.transition_job(
                job_id=job.id,
                organization_id=organization_id,
                new_status=CommunicationJobStatus.COMPLETED,
            )
            return MessageJobResult(CommunicationJobStatus.COMPLETED, message.id)

        await self.job_service.transition_job(
            job_id=job.id,
            organization_id=organization_id,
            new_status=CommunicationJobStatus.FAILED,
            reason_code=dispatched.error_code or "MESSAGE_DISPATCH_FAILED",
            reason=dispatched.error_message or "The message provider rejected the message.",
        )
        return MessageJobResult(
            CommunicationJobStatus.FAILED,
            message.id,
            dispatched.error_code or "MESSAGE_DISPATCH_FAILED",
        )

    async def _fail_existing_message(self, job: Any, message: Any) -> MessageJobResult:
        reason_code = message.error_code or "MESSAGE_NOT_DISPATCHABLE"
        await self.job_service.transition_job(
            job_id=job.id,
            organization_id=job.organization_id,
            new_status=CommunicationJobStatus.FAILED,
            reason_code=reason_code,
            reason=message.error_message or "The existing message cannot be dispatched again.",
        )
        return MessageJobResult(CommunicationJobStatus.FAILED, message.id, reason_code)

    async def _get_or_suppress(
        self,
        repository: Any,
        method_name: str,
        **filters: Any,
    ) -> Any | None:
        entity = await getattr(repository, method_name)(**filters)
        return entity

    async def _suppress(self, job: Any, reason_code: str, reason: str) -> MessageJobResult:
        await self.job_service.transition_job(
            job_id=job.id,
            organization_id=job.organization_id,
            new_status=CommunicationJobStatus.SUPPRESSED,
            reason_code=reason_code,
            reason=reason,
        )
        return MessageJobResult(CommunicationJobStatus.SUPPRESSED, reason_code=reason_code)

    @staticmethod
    def _due_date(work_item: Any) -> date | None:
        return work_item.due_at.date() if work_item and work_item.due_at else None

    @staticmethod
    def _is_retryable_error(error_code: str | None) -> bool:
        """Classify common transient provider failures without naming a vendor."""
        if not error_code:
            return False
        normalized = error_code.upper()
        return any(
            marker in normalized
            for marker in ("NETWORK", "TIMEOUT", "429", "HTTP_5", "RATE_LIMIT", "TRANSIENT")
        )


__all__ = ["MessageJobProcessor", "MessageJobResult"]
