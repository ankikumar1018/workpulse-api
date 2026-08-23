"""Department response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class DepartmentResponse(BaseModel):
    """Public department representation."""

    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = ["DepartmentResponse"]
