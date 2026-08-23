"""Organization response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel


class OrganizationResponse(BaseModel):
    """Organization response."""

    id: UUID
    name: str
    slug: str
    status: str
    subscription_status: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={"example": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Acme Corp",
        "slug": "acme-corp",
        "status": "active",
        "subscription_status": "active",
        "created_at": "2026-01-15T10:30:00Z",
        "updated_at": "2026-01-15T10:30:00Z",
        }},
    )


__all__ = ["OrganizationResponse"]
