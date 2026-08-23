"""Authentication request schemas."""

from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["admin"]
UserStatus = Literal["active", "inactive"]


class UserCreateRequest(BaseModel):
    """Create an administrator user."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    role: UserRole = "admin"
    status: UserStatus = "active"


class UserUpdateRequest(BaseModel):
    """Partially update an administrator user."""

    email: str | None = Field(None, min_length=3, max_length=320)
    password: str | None = Field(None, min_length=8, max_length=256)
    role: UserRole | None = None
    status: UserStatus | None = None


class RefreshTokenRequest(BaseModel):
    """Request body for refreshing an access token."""

    refresh_token: str = Field(min_length=1)


__all__ = [
    "RefreshTokenRequest",
    "UserCreateRequest",
    "UserRole",
    "UserStatus",
    "UserUpdateRequest",
]
