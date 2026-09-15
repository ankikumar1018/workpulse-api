"""Tests for the provider-agnostic message domain model."""

from uuid import uuid4

import pytest

from app.domain.enums import Channel, DeliveryStatus
from app.domain.message import InvalidMessageTransitionError, Message


def make_message() -> Message:
    """Build a minimal logical message for domain tests."""
    return Message(
        id=uuid4(),
        organization_id=uuid4(),
        worker_id=uuid4(),
        channel=Channel.WHATSAPP,
        recipient_phone_number="+15551234567",
        rendered_body="Kitchen cabinets are ready for review.",
        dispatch_key="project-1:daily-status:worker-1",
    )


def test_message_captures_provider_agnostic_intent_and_recipient() -> None:
    message = make_message()

    assert message.channel == Channel.WHATSAPP
    assert message.delivery_status == DeliveryStatus.QUEUED
    assert message.provider_name is None
    assert message.provider_message_id is None


def test_message_can_progress_from_queued_to_delivered() -> None:
    message = make_message()

    message.transition_to(DeliveryStatus.SENT)
    message.provider_name = "test-provider"
    message.provider_message_id = "provider-message-1"
    message.transition_to(DeliveryStatus.DELIVERED)

    assert message.delivery_status == DeliveryStatus.DELIVERED
    assert message.provider_name == "test-provider"
    assert message.provider_message_id == "provider-message-1"


def test_message_rejects_invalid_terminal_transition() -> None:
    message = make_message()
    message.transition_to(DeliveryStatus.FAILED)

    with pytest.raises(InvalidMessageTransitionError, match="Cannot transition message"):
        message.transition_to(DeliveryStatus.SENT)