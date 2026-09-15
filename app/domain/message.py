"""Provider-agnostic outbound message domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from app.domain.enums import Channel, DeliveryStatus


class InvalidMessageTransitionError(Exception):
    """Raised when an outbound message changes to an invalid delivery state."""


@dataclass
class Message:
    """Logical outbound message independent of any provider payload format."""

    id: UUID
    organization_id: UUID
    worker_id: UUID
    channel: Channel
    recipient_phone_number: str
    rendered_body: str
    dispatch_key: str
    delivery_status: DeliveryStatus = DeliveryStatus.QUEUED
    work_item_id: UUID | None = None
    schedule_id: UUID | None = None
    provider_name: str | None = None
    provider_message_id: str | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None

    VALID_TRANSITIONS: ClassVar[dict[DeliveryStatus, set[DeliveryStatus]]] = {
        DeliveryStatus.QUEUED: {DeliveryStatus.SENT, DeliveryStatus.FAILED},
        DeliveryStatus.SENT: {DeliveryStatus.DELIVERED, DeliveryStatus.FAILED},
        DeliveryStatus.DELIVERED: set(),
        DeliveryStatus.FAILED: set(),
    }

    def can_transition_to(self, new_status: DeliveryStatus) -> bool:
        """Return whether the message can move to the requested delivery state."""
        return new_status in self.VALID_TRANSITIONS.get(self.delivery_status, set())

    def transition_to(self, new_status: DeliveryStatus) -> None:
        """Move the message through its provider-agnostic delivery lifecycle."""
        if new_status == self.delivery_status:
            return
        if not self.can_transition_to(new_status):
            allowed = self.VALID_TRANSITIONS.get(self.delivery_status, set())
            allowed_values = ", ".join(
                status.value for status in sorted(allowed, key=lambda status: status.value)
            )
            raise InvalidMessageTransitionError(
                f"Cannot transition message from '{self.delivery_status.value}' to "
                f"'{new_status.value}'. Allowed transitions: {allowed_values}"
            )
        self.delivery_status = new_status


__all__ = ["InvalidMessageTransitionError", "Message"]