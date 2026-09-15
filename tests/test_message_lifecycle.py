from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.enums import Channel, DeliveryStatus
from app.domain.idempotency import (
    build_communication_job_key,
    build_message_dispatch_key,
)
from app.infrastructure.db.models import Message as MessageModel, MessageStatusHistory
from app.repositories.message import MessageHistoryRepository
from app.services.message import MessageService


class FakeSession:
    async def commit(self):
        pass

    async def refresh(self, _message):
        pass


class FakeMessageRepository:
    def __init__(self, messages: list[MessageModel]):
        self.messages = messages
        self.session = FakeSession()
        self.history: list[MessageStatusHistory] = []

    async def get_in_organization(self, *, message_id, organization_id):
        return next(
            (
                message
                for message in self.messages
                if message.id == message_id and message.organization_id == organization_id
            ),
            None,
        )

    async def find_by_dispatch_key(self, *, organization_id, dispatch_key):
        return next(
            (
                message
                for message in self.messages
                if message.organization_id == organization_id
                and message.dispatch_key == dispatch_key
            ),
            None,
        )

    async def create_idempotent(self, message_data):
        existing = await self.find_by_dispatch_key(
            organization_id=message_data["organization_id"],
            dispatch_key=message_data["dispatch_key"],
        )
        if existing is not None:
            return existing
        message = MessageModel(id=uuid4(), delivery_status=DeliveryStatus.QUEUED, **message_data)
        self.messages.append(message)
        return message

    async def save_transition(self, *, message, previous_status, actor_user_id, occurred_at):
        history = MessageStatusHistory(
            id=uuid4(),
            organization_id=message.organization_id,
            message_id=message.id,
            previous_status=previous_status,
            new_status=message.delivery_status,
            actor_user_id=actor_user_id,
            provider_name=message.provider_name,
            provider_message_id=message.provider_message_id,
            error_code=message.error_code,
            error_message=message.error_message,
            created_at=occurred_at,
        )
        self.history.append(history)
        return history


class FakeHistoryRepository(MessageHistoryRepository):
    def __init__(self, repository: FakeMessageRepository):
        self.repository = repository

    async def list_for_message(self, *, message_id, organization_id):
        return [
            history
            for history in self.repository.history
            if history.message_id == message_id and history.organization_id == organization_id
        ]


def make_message(*, organization_id=None):
    return MessageModel(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        worker_id=uuid4(),
        channel=Channel.WHATSAPP,
        recipient_phone_number="+15551234567",
        rendered_body="Work update",
        dispatch_key="project-1:daily-status:worker-1",
        delivery_status=DeliveryStatus.QUEUED,
    )


def test_idempotency_keys_are_stable_and_distinct_by_logical_execution():
    inputs = {
        "organization_id": uuid4(),
        "schedule_id": uuid4(),
        "template_id": uuid4(),
        "worker_id": uuid4(),
        "execution_at": datetime(2026, 9, 15, 12, 30, tzinfo=UTC),
    }

    message_key = build_message_dispatch_key(**inputs)
    assert message_key == build_message_dispatch_key(**inputs)
    assert message_key.startswith("msg_")
    assert build_communication_job_key(**inputs).startswith("job_")
    assert build_message_dispatch_key(
        **{**inputs, "execution_at": datetime(2026, 9, 15, 12, 31, tzinfo=UTC)}
    ) != message_key

    with pytest.raises(ValueError, match="timezone"):
        build_message_dispatch_key(**{**inputs, "execution_at": datetime(2026, 9, 15, 12, 30)})


@pytest.mark.asyncio
async def test_message_service_records_tenant_scoped_transition_history():
    organization_id = uuid4()
    message = make_message(organization_id=organization_id)
    repository = FakeMessageRepository([message])
    service = MessageService(repository, FakeHistoryRepository(repository))
    occurred_at = datetime(2026, 9, 15, 12, 30, tzinfo=UTC)

    updated = await service.transition_message(
        message_id=message.id,
        organization_id=organization_id,
        new_status=DeliveryStatus.SENT,
        actor_user_id=uuid4(),
        provider_name="test-provider",
        provider_message_id="provider-1",
        occurred_at=occurred_at,
    )

    assert updated.delivery_status == DeliveryStatus.SENT
    assert updated.sent_at == occurred_at
    assert repository.history[0].previous_status == DeliveryStatus.QUEUED
    assert repository.history[0].new_status == DeliveryStatus.SENT
    assert repository.history[0].provider_message_id == "provider-1"
    assert await service.list_history(
        message_id=message.id,
        organization_id=organization_id,
    ) == repository.history

    with pytest.raises(NotFoundError):
        await service.get_message(message_id=message.id, organization_id=uuid4())


@pytest.mark.asyncio
async def test_message_creation_reuses_the_same_logical_dispatch():
    repository = FakeMessageRepository([])
    service = MessageService(repository, FakeHistoryRepository(repository))
    inputs = {
        "organization_id": uuid4(),
        "schedule_id": uuid4(),
        "template_id": uuid4(),
        "work_item_id": uuid4(),
        "worker_id": uuid4(),
        "channel": Channel.WHATSAPP,
        "recipient_phone_number": "+15551234567",
        "rendered_body": "Work update",
        "execution_at": datetime(2026, 9, 15, 12, 30, tzinfo=UTC),
    }

    first = await service.create_message(**inputs)
    second = await service.create_message(**inputs)

    assert second.id == first.id
    assert second.dispatch_key == first.dispatch_key
    assert len(repository.messages) == 1


@pytest.mark.asyncio
async def test_message_service_rejects_invalid_transition_without_history():
    message = make_message()
    repository = FakeMessageRepository([message])
    service = MessageService(repository, FakeHistoryRepository(repository))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.transition_message(
            message_id=message.id,
            organization_id=message.organization_id,
            new_status=DeliveryStatus.DELIVERED,
        )

    assert "Cannot transition message" in exception_info.value.message
    assert repository.history == []
