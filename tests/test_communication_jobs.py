from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.enums import Channel, CommunicationJobStatus
from app.domain.idempotency import build_communication_job_key
from app.infrastructure.db.models import CommunicationJob, CommunicationJobStatusHistory
from app.repositories.communication_job import CommunicationJobHistoryRepository
from app.services.communication_job import CommunicationJobService


class FakeSession:
    async def commit(self):
        pass

    async def refresh(self, _entity):
        pass


class FakeCommunicationJobRepository:
    def __init__(self, jobs: list[CommunicationJob]):
        self.jobs = jobs
        self.session = FakeSession()
        self.history: list[CommunicationJobStatusHistory] = []

    async def get_in_organization(self, *, job_id, organization_id):
        return next(
            (
                job
                for job in self.jobs
                if job.id == job_id and job.organization_id == organization_id
            ),
            None,
        )

    async def find_by_job_key(self, *, organization_id, job_key):
        return next(
            (
                job
                for job in self.jobs
                if job.organization_id == organization_id and job.job_key == job_key
            ),
            None,
        )

    async def create_idempotent(self, job_data):
        existing = await self.find_by_job_key(
            organization_id=job_data["organization_id"], job_key=job_data["job_key"]
        )
        if existing is not None:
            return existing
        job = CommunicationJob(id=uuid4(), **job_data)
        self.jobs.append(job)
        return job

    async def save_transition(
        self,
        *,
        job,
        previous_status,
        new_status,
        reason_code,
        reason,
        queue_reference,
        occurred_at,
    ):
        history = CommunicationJobStatusHistory(
            id=uuid4(),
            organization_id=job.organization_id,
            job_id=job.id,
            previous_status=previous_status,
            new_status=new_status,
            reason_code=reason_code,
            reason=reason,
            queue_reference=queue_reference,
            created_at=occurred_at,
        )
        self.history.append(history)
        return history


class FakeHistoryRepository(CommunicationJobHistoryRepository):
    def __init__(self, repository: FakeCommunicationJobRepository):
        self.repository = repository

    async def list_for_job(self, *, job_id, organization_id):
        return [
            history
            for history in self.repository.history
            if history.job_id == job_id and history.organization_id == organization_id
        ]


def job_inputs(*, organization_id=None):
    return {
        "organization_id": organization_id or uuid4(),
        "schedule_id": uuid4(),
        "template_id": uuid4(),
        "work_item_id": uuid4(),
        "worker_id": uuid4(),
        "channel": Channel.WHATSAPP,
        "execution_at": datetime(2026, 10, 1, 12, 30, tzinfo=UTC),
    }


@pytest.mark.asyncio
async def test_job_creation_is_idempotent_and_queue_independent():
    repository = FakeCommunicationJobRepository([])
    service = CommunicationJobService(repository, FakeHistoryRepository(repository))
    inputs = job_inputs()

    first = await service.create_job(**inputs)
    second = await service.create_job(**inputs)

    assert second.id == first.id
    assert second.job_key == build_communication_job_key(
        organization_id=inputs["organization_id"],
        schedule_id=inputs["schedule_id"],
        template_id=inputs["template_id"],
        worker_id=inputs["worker_id"],
        execution_at=inputs["execution_at"],
    )
    assert second.status == CommunicationJobStatus.PENDING
    assert len(repository.jobs) == 1


@pytest.mark.asyncio
async def test_job_transitions_record_attempts_and_queue_outcomes():
    repository = FakeCommunicationJobRepository([])
    service = CommunicationJobService(repository, FakeHistoryRepository(repository))
    job = await service.create_job(**job_inputs())
    started_at = datetime(2026, 10, 1, 12, 31, tzinfo=UTC)

    processing = await service.transition_job(
        job_id=job.id,
        organization_id=job.organization_id,
        new_status=CommunicationJobStatus.PROCESSING,
        queue_reference="tasks/123",
        occurred_at=started_at,
    )
    failed = await service.transition_job(
        job_id=job.id,
        organization_id=job.organization_id,
        new_status=CommunicationJobStatus.FAILED,
        reason_code="QUEUE_UNAVAILABLE",
        reason="Cloud Tasks rejected the request",
        queue_reference="tasks/123",
        occurred_at=started_at,
    )

    assert processing.attempt_count == 1
    assert failed.status == CommunicationJobStatus.FAILED
    assert failed.last_error_code == "QUEUE_UNAVAILABLE"
    assert len(await service.list_history(job_id=job.id, organization_id=job.organization_id)) == 2
    assert repository.history[-1].queue_reference == "tasks/123"


@pytest.mark.asyncio
async def test_job_reads_are_tenant_scoped_and_invalid_transitions_are_rejected():
    repository = FakeCommunicationJobRepository([])
    service = CommunicationJobService(repository, FakeHistoryRepository(repository))
    job = await service.create_job(**job_inputs())

    with pytest.raises(NotFoundError):
        await service.get_job(job_id=job.id, organization_id=uuid4())

    with pytest.raises(UnprocessableEntityError):
        await service.transition_job(
            job_id=job.id,
            organization_id=job.organization_id,
            new_status=CommunicationJobStatus.COMPLETED,
        )
