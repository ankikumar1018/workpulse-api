"""Communication job and delivery dashboard response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class CommunicationJobResponse(BaseModel):
    """Public logical communication job representation."""

    id: UUID
    organization_id: UUID
    schedule_id: UUID | None
    template_id: UUID
    work_item_id: UUID | None
    worker_id: UUID
    channel: str
    execution_at: datetime
    status: str
    attempt_count: int
    last_error_code: str | None
    last_error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CommunicationJobHistoryResponse(BaseModel):
    """One persisted logical job status transition."""

    id: UUID
    organization_id: UUID
    job_id: UUID
    previous_status: str | None
    new_status: str
    reason_code: str | None
    reason: str | None
    queue_reference: str | None
    created_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MessageResponse(BaseModel):
    """Public outbound message representation for operational review."""

    id: UUID
    organization_id: UUID
    schedule_id: UUID | None
    work_item_id: UUID | None
    worker_id: UUID
    channel: str
    recipient_phone_number: str
    rendered_body: str
    provider_name: str | None
    provider_message_id: str | None
    delivery_status: str
    error_code: str | None
    error_message: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = [
    "CommunicationJobHistoryResponse",
    "CommunicationJobResponse",
    "MessageResponse",
]
