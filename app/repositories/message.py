"""Outbound message and lifecycle-history persistence operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import DeliveryStatus
from app.infrastructure.db.models import Message, MessageStatusHistory
from app.infrastructure.repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Tenant-scoped outbound message repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Message)

    async def get_in_organization(
        self,
        *,
        message_id: UUID,
        organization_id: UUID,
    ) -> Message | None:
        result = await self.session.execute(
            select(Message).where(
                Message.id == message_id,
                Message.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_dispatch_key(
        self,
        *,
        organization_id: UUID,
        dispatch_key: str,
    ) -> Message | None:
        result = await self.session.execute(
            select(Message).where(
                Message.organization_id == organization_id,
                Message.dispatch_key == dispatch_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_idempotent(self, message_data: dict[str, Any]) -> Message:
        existing = await self.find_by_dispatch_key(
            organization_id=message_data["organization_id"],
            dispatch_key=message_data["dispatch_key"],
        )
        if existing is not None:
            return existing
        message = Message(**message_data)
        self.session.add(message)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.find_by_dispatch_key(
                organization_id=message_data["organization_id"],
                dispatch_key=message_data["dispatch_key"],
            )
            if existing is not None:
                return existing
            raise
        await self.session.refresh(message)
        return message

    async def save_transition(
        self,
        *,
        message: Message,
        previous_status: DeliveryStatus,
        actor_user_id: UUID | None,
        occurred_at: datetime,
    ) -> MessageStatusHistory:
        history = MessageStatusHistory(
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
        self.session.add(message)
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(message)
        await self.session.refresh(history)
        return history


class MessageHistoryRepository:
    """Read-only tenant-scoped message history queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_message(
        self,
        *,
        message_id: UUID,
        organization_id: UUID,
    ) -> list[MessageStatusHistory]:
        result = await self.session.execute(
            select(MessageStatusHistory)
            .where(
                MessageStatusHistory.message_id == message_id,
                MessageStatusHistory.organization_id == organization_id,
            )
            .order_by(MessageStatusHistory.created_at, MessageStatusHistory.id)
        )
        return list(result.scalars().all())


__all__ = ["MessageHistoryRepository", "MessageRepository"]
