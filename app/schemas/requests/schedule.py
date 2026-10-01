"""Schedule configuration request schemas."""

from __future__ import annotations

from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import to_camel


class ScheduleCreateRequest(BaseModel):
    """Create a paused project schedule."""

    department_id: UUID
    template_id: UUID
    timezone: str = Field(min_length=1, max_length=64)
    window_start_local: time
    window_end_local: time
    interval_seconds: int = Field(gt=0, le=31_536_000)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ScheduleUpdateRequest(BaseModel):
    """Update configuration on a paused schedule."""

    department_id: UUID | None = None
    template_id: UUID | None = None
    timezone: str | None = Field(None, min_length=1, max_length=64)
    window_start_local: time | None = None
    window_end_local: time | None = None
    interval_seconds: int | None = Field(None, gt=0, le=31_536_000)

    model_config = ScheduleCreateRequest.model_config


__all__ = ["ScheduleCreateRequest", "ScheduleUpdateRequest"]
