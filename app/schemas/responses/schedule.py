"""Schedule response schema."""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class ScheduleResponse(BaseModel):
    """Public schedule representation."""

    id: UUID
    organization_id: UUID
    project_id: UUID
    department_id: UUID
    template_id: UUID
    timezone: str
    window_start_local: time
    window_end_local: time
    interval_seconds: int
    status: str
    next_run_at_utc: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = ["ScheduleResponse"]
