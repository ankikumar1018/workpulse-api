"""Outbound message lifecycle business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.enums import Channel, DeliveryStatus
from app.domain.idempotency import build_message_dispatch_key
from app.domain.message import InvalidMessageTransitionError, Message as MessageDomain
from app.infrastructure.db.models import Message
from app.repositories.message import MessageHistoryRepository, MessageRepository


class MessageService:
    """Apply transition-safe delivery updates and preserve their history."""

    def __init__(
        self,
        repository: MessageRepository,
        history_repository: MessageHistoryRepository | None = None,
    ):
        self.repository = repository
        self.history_repository = history_repository

    async def get_message(self, *, message_id: UUID, organization_id: UUID) -> Message:
        message = await self.repository.get_in_organization(
            message_id=message_id,
            organization_id=organization_id,
        )
        if message is None:
            raise NotFoundError(f"Message '{message_id}' not found")
        return message

    async def create_message(
        self,
        *,
        organization_id: UUID,
        schedule_id: UUID,
        template_id: UUID,
        work_item_id: UUID | None,
        worker_id: UUID,
        channel: Channel,
        recipient_phone_number: str,
        rendered_body: str,
        execution_at: datetime,
    ) -> Message:
        """Create or reuse one logical message for a scheduled execution."""
        dispatch_key = build_message_dispatch_key(
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
                "work_item_id": work_item_id,
                "worker_id": worker_id,
                "channel": channel,
                "recipient_phone_number": recipient_phone_number,
                "rendered_body": rendered_body,
                "dispatch_key": dispatch_key,
            }
        )

    async def transition_message(
        self,
        *,
        message_id: UUID,
        organization_id: UUID,
        new_status: DeliveryStatus,
        actor_user_id: UUID | None = None,
        provider_name: str | None = None,
        provider_message_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        occurred_at: datetime | None = None,
    ) -> Message:
        message = await self.get_message(message_id=message_id, organization_id=organization_id)
        previous_status = message.delivery_status
        domain_message = MessageDomain(
            id=message.id,
            organization_id=message.organization_id,
            worker_id=message.worker_id,
            channel=message.channel,
            recipient_phone_number=message.recipient_phone_number,
            rendered_body=message.rendered_body,
            dispatch_key=message.dispatch_key,
            delivery_status=message.delivery_status,
            work_item_id=message.work_item_id,
            schedule_id=message.schedule_id,
            provider_name=message.provider_name,
            provider_message_id=message.provider_message_id,
            sent_at=message.sent_at,
            delivered_at=message.delivered_at,
        )
        try:
            domain_message.transition_to(new_status)
        except InvalidMessageTransitionError as exc:
            raise UnprocessableEntityError(str(exc)) from exc

        occurred_at = occurred_at or datetime.now(UTC)
        message.delivery_status = domain_message.delivery_status
        message.provider_name = provider_name or message.provider_name
        message.provider_message_id = provider_message_id or message.provider_message_id
        message.error_code = error_code
        message.error_message = error_message
        if new_status == DeliveryStatus.SENT:
            message.sent_at = occurred_at
        if new_status == DeliveryStatus.DELIVERED:
            message.delivered_at = occurred_at
        if self.history_repository is None:
            await self.repository.session.commit()
            await self.repository.session.refresh(message)
        else:
            await self.repository.save_transition(
                message=message,
                previous_status=previous_status,
                actor_user_id=actor_user_id,
                occurred_at=occurred_at,
            )
        return message

    async def list_history(
        self,
        *,
        message_id: UUID,
        organization_id: UUID,
    ) -> list:
        await self.get_message(message_id=message_id, organization_id=organization_id)
        if self.history_repository is None:
            return []
        return await self.history_repository.list_for_message(
            message_id=message_id,
            organization_id=organization_id,
        )


__all__ = ["MessageService"]
