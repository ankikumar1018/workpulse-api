"""Authentication response schemas."""

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """OAuth2-compatible access and refresh token response."""

    access_token: str = Field(description="Short-lived bearer access token")
    refresh_token: str = Field(description="Rotatable refresh token")
    token_type: str = Field(default="bearer")


__all__ = ["TokenResponse"]
