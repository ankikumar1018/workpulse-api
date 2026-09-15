"""Outbound message history response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class MessageHistoryResponse(BaseModel):
    """Public delivery state history entry."""

    id: UUID
    organization_id: UUID
    message_id: UUID
    previous_status: str | None
    new_status: str
    actor_user_id: UUID | None
    provider_name: str | None
    provider_message_id: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = ["MessageHistoryResponse"]
