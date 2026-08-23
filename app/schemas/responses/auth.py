"""Authentication response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import to_camel


class TokenResponse(BaseModel):
    """OAuth2-compatible access and refresh token response."""

    access_token: str = Field(description="Short-lived bearer access token")
    refresh_token: str = Field(description="Rotatable refresh token")
    token_type: str = Field(default="bearer")


class UserResponse(BaseModel):
    """Public administrator user representation."""

    id: UUID
    organization_id: UUID
    email: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = ["TokenResponse", "UserResponse"]
