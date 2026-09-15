"""Outbound message history API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, MessageSvc
from app.api.utils import make_success_response
from app.infrastructure.db.models import MessageStatusHistory
from app.schemas import MessageHistoryResponse, SuccessEnvelope

router = APIRouter(prefix="/messages", tags=["Messages"])


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
