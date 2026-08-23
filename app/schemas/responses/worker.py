"""Worker response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class WorkerResponse(BaseModel):
    """Public worker representation."""

    id: UUID
    organization_id: UUID
    department_id: UUID
    full_name: str
    phone_number: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = ["WorkerResponse"]
