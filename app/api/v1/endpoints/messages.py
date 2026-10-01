"""Outbound message history API endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, MessageSvc
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.domain.enums import DeliveryStatus
from app.infrastructure.db.models import Message, MessageStatusHistory
from app.schemas import ListEnvelope, MessageHistoryResponse, SuccessEnvelope
from app.schemas.responses.communication import MessageResponse

router = APIRouter(prefix="/messages", tags=["Messages"])


def to_message_response(message: Message) -> MessageResponse:
    """Convert an outbound message to its public operational representation."""
    return MessageResponse(
        id=message.id,
        organization_id=message.organization_id,
        schedule_id=message.schedule_id,
        work_item_id=message.work_item_id,
        worker_id=message.worker_id,
        channel=message.channel.value,
        recipient_phone_number=message.recipient_phone_number,
        rendered_body=message.rendered_body,
        provider_name=message.provider_name,
        provider_message_id=message.provider_message_id,
        delivery_status=message.delivery_status.value,
        error_code=message.error_code,
        error_message=message.error_message,
        sent_at=message.sent_at,
        delivered_at=message.delivered_at,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


@router.get("", response_model=ListEnvelope)
async def list_messages(
    controller: MessageSvc,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    delivery_status: Annotated[DeliveryStatus | None, Query(alias="status")] = None,
):
    """List outbound messages for the current organization."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    messages, total = await controller.list_messages(
        organization_id=current_user.organization_id,
        status=delivery_status,
        limit=limit,
        offset=offset,
    )
    return make_list_response(
        [to_message_response(message) for message in messages], total, limit, offset
    )


def to_message_history_response(history: MessageStatusHistory) -> MessageHistoryResponse:
    """Convert a message history ORM object to its public representation."""
    return MessageHistoryResponse(
        id=history.id,
        organization_id=history.organization_id,
        message_id=history.message_id,
        previous_status=history.previous_status.value if history.previous_status else None,
        new_status=history.new_status.value,
        actor_user_id=history.actor_user_id,
        provider_name=history.provider_name,
        provider_message_id=history.provider_message_id,
        error_code=history.error_code,
        error_message=history.error_message,
        created_at=history.created_at,
    )


@router.get("/{message_id}/history", response_model=SuccessEnvelope)
async def list_message_history(
    message_id: UUID,
    controller: MessageSvc,
    current_user: CurrentUser,
):
    """List the tenant-scoped delivery history for an outbound message."""
    current_user.assert_admin()
    history = await controller.list_history(
        message_id=message_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response([to_message_history_response(entry) for entry in history])


__all__ = ["router"]
