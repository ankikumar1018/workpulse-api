"""Work item response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class WorkItemResponse(BaseModel):
    """Public work item representation."""

    id: UUID
    organization_id: UUID
    project_id: UUID
    department_id: UUID
    worker_id: UUID | None
    title: str
    description: str | None
    priority: str
    status: str
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WorkItemTransitionResponse(BaseModel):
    """Response for a work item status transition."""

    work_item_id: UUID
    old_status: str
    new_status: str
    timestamp: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = ["WorkItemResponse", "WorkItemTransitionResponse"]
