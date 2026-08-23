"""Project response schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class ProjectResponse(BaseModel):
    """Public project representation."""

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    status: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = ["ProjectResponse"]
