"""Authentication request schemas."""

from pydantic import BaseModel, Field


class RefreshTokenRequest(BaseModel):
    """Request body for refreshing an access token."""

    refresh_token: str = Field(min_length=1)


__all__ = ["RefreshTokenRequest"]
