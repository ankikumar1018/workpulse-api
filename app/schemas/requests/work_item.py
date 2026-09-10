"""Work item request schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

WorkPriority = Literal["low", "medium", "high", "urgent"]
WorkStatus = Literal["open", "in_progress", "blocked", "done", "cancelled"]


class WorkItemCreateRequest(BaseModel):
    """Create a work item in a project and department."""

    department_id: UUID = Field(description="Department ID where the work item belongs")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=65535)
    priority: WorkPriority = "medium"
    worker_id: UUID | None = None
    due_at: datetime | None = None


class WorkItemUpdateStatusRequest(BaseModel):
    """Update a work item's status."""

    status: WorkStatus = Field(
        description="New status for the work item. Must be a valid transition."
    )


class WorkItemUpdateRequest(BaseModel):
    """Partially update a work item."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=65535)
    priority: WorkPriority | None = None
    status: WorkStatus | None = None
    worker_id: UUID | None = None


__all__ = [
    "WorkItemCreateRequest",
    "WorkItemUpdateRequest",
    "WorkItemUpdateStatusRequest",
    "WorkPriority",
    "WorkStatus",
]
