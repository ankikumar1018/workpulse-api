from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.enums import (
    CommunicationJobStatus,
    ConsentStatus,
    DeliveryStatus,
    EntityStatus,
    ScheduleStatus,
    WorkerStatus,
    WorkStatus,
)
from app.services.message_job_processor import MessageJobProcessor


class FakeRepository:
    def __init__(self, entities):
        self.entities = entities

    async def get_in_organization(self, **filters):
        entity_id = next(value for key, value in filters.items() if key.endswith("_id"))
        return self.entities.get(entity_id)


class FakeJobService:
    def __init__(self, job):
        self.job = job
        self.transitions = []

    async def get_job(self, **_filters):
        return self.job

    async def transition_job(self, **transition):
        self.transitions.append(transition)
        self.job.status = transition["new_status"]
        return self.job


class FakeMessageService:
    def __init__(self, message):
        self.message = message
        self.created = []
        self.dispatch_count = 0

    async def create_message(self, **data):
        self.created.append(data)
        return self.message

    async def dispatch_message(self, **_data):
        self.dispatch_count += 1
        self.message.delivery_status = DeliveryStatus.SENT
        return self.message


class FakeTemplateService:
    def __init__(self, template):
        self.template = template
        self.context = None

    async def get_template(self, **_filters):
        return self.template

    async def render_template(self, *, context, **_filters):
        self.context = context
        return f"Hello {context.primary_contact_name}"


def build_processor(*, worker_status=WorkerStatus.ACTIVE, consent=ConsentStatus.OPTED_IN):
    organization_id = uuid4()
    schedule_id = uuid4()
    project_id = uuid4()
    department_id = uuid4()
    worker_id = uuid4()
    template_id = uuid4()
    work_item_id = uuid4()
    job = SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        schedule_id=schedule_id,
        project_id=project_id,
        template_id=template_id,
        work_item_id=work_item_id,
        worker_id=worker_id,
        channel="whatsapp",
        execution_at=datetime(2026, 10, 1, 12, 30, tzinfo=UTC),
        status=CommunicationJobStatus.PENDING,
    )
    schedule = SimpleNamespace(
        id=schedule_id,
        organization_id=organization_id,
        project_id=project_id,
        department_id=department_id,
        status=ScheduleStatus.ACTIVE,
    )
    project = SimpleNamespace(
        id=project_id, organization_id=organization_id, name="Apollo", status=EntityStatus.ACTIVE
    )
    department = SimpleNamespace(id=department_id, organization_id=organization_id, name="Support")
    worker = SimpleNamespace(
        id=worker_id,
        organization_id=organization_id,
        full_name="Ada Lovelace",
        phone_number="+14155550100",
        contact_channel="whatsapp",
        status=worker_status,
        consent_status=consent,
    )
    work_item = SimpleNamespace(
        id=work_item_id,
        organization_id=organization_id,
        title="Review queue",
        status=WorkStatus.IN_PROGRESS,
        priority=SimpleNamespace(value="high"),
        due_at=None,
    )
    template = SimpleNamespace(id=template_id, channel="whatsapp", status=EntityStatus.ACTIVE)
    message = SimpleNamespace(id=uuid4(), delivery_status=DeliveryStatus.QUEUED)
    job_service = FakeJobService(job)
    message_service = FakeMessageService(message)
    template_service = FakeTemplateService(template)
    processor = MessageJobProcessor(
        job_service=job_service,
        message_service=message_service,
        schedule_repository=FakeRepository({schedule_id: schedule}),
        project_repository=FakeRepository({project_id: project}),
        department_repository=FakeRepository({department_id: department}),
        worker_repository=FakeRepository({worker_id: worker}),
        work_item_repository=FakeRepository({work_item_id: work_item}),
        template_service=template_service,
    )
    return processor, job, job_service, message_service, template_service


@pytest.mark.asyncio
async def test_processor_revalidates_renders_and_dispatches_current_state():
    processor, job, job_service, message_service, template_service = build_processor()

    result = await processor.process(
        job_id=job.id,
        organization_id=job.organization_id,
        provider=object(),
    )

    assert result.job_status == CommunicationJobStatus.COMPLETED
    assert message_service.created[0]["rendered_body"] == "Hello Ada Lovelace"
    assert template_service.context.project_name == "Apollo"
    assert message_service.dispatch_count == 1
    assert [item["new_status"] for item in job_service.transitions] == [
        CommunicationJobStatus.PROCESSING,
        CommunicationJobStatus.COMPLETED,
    ]


@pytest.mark.asyncio
async def test_processor_suppresses_worker_without_consent_before_rendering():
    processor, job, job_service, message_service, _template_service = build_processor(
        consent=ConsentStatus.OPTED_OUT
    )

    result = await processor.process(
        job_id=job.id,
        organization_id=job.organization_id,
        provider=object(),
    )

    assert result.job_status == CommunicationJobStatus.SUPPRESSED
    assert result.reason_code == "CONSENT_REQUIRED"
    assert job_service.transitions[-1]["reason_code"] == "CONSENT_REQUIRED"
    assert message_service.created == []


@pytest.mark.asyncio
async def test_processor_does_not_send_an_already_sent_message_again():
    processor, job, _job_service, message_service, _template_service = build_processor()
    message_service.message.delivery_status = DeliveryStatus.SENT

    result = await processor.process(
        job_id=job.id,
        organization_id=job.organization_id,
        provider=object(),
    )

    assert result.job_status == CommunicationJobStatus.COMPLETED
    assert message_service.dispatch_count == 0
