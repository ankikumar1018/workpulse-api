"""Organization request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OrganizationCreateRequest(BaseModel):
    """Create organization request."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization display name",
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="URL-safe unique slug",
    )

    model_config = {"json_schema_extra": {"example": {
        "name": "Acme Interior Design",
        "slug": "acme-corp",
    }}}


class OrganizationUpdateRequest(BaseModel):
    """Update organization request (partial)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(
        None,
        description="'provisioning', 'active', 'inactive', 'suspended', 'archived'",
    )
    subscription_status: str | None = Field(
        None,
        description="'trialing', 'active', 'past_due', 'canceled', 'expired'",
    )

    model_config = {"json_schema_extra": {"example": {
        "status": "active",
    }}}


__all__ = ["OrganizationCreateRequest", "OrganizationUpdateRequest"]
