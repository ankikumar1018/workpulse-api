"""API dependency injection and authorization."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.api.errors import ForbiddenError, UnauthorizedError
from app.api.security import decode_access_token


class AuthContext:
    """Current user authentication context."""

    def __init__(
        self,
        user_id: UUID,
        organization_id: UUID,
        role: str = "admin",
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role

    def assert_admin(self) -> None:
        """Verify user has admin role."""
        if self.role != "admin":
            raise ForbiddenError("Admin role required")

    def assert_organization(self, org_id: UUID) -> None:
        """Verify user belongs to the requested organization."""
        if self.organization_id != org_id:
            raise ForbiddenError("Organization access denied")


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    refreshUrl="/api/v1/auth/refresh",
    auto_error=False,
)


async def get_auth_context(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> AuthContext:
    """Decode and validate the bearer token supplied by FastAPI's OAuth2 scheme."""
    if not token:
        raise UnauthorizedError("Missing bearer token")

    try:
        claims = decode_access_token(token)
        return AuthContext(
            user_id=UUID(claims["user_id"]),
            organization_id=UUID(claims["organization_id"]),
            role=claims["role"],
        )
    except ValueError as exc:
        raise UnauthorizedError("Invalid access token") from exc


# Type alias for dependency injection
CurrentUser = Annotated[AuthContext, Depends(get_auth_context)]


__all__ = [
    "AuthContext",
    "CurrentUser",
    "get_auth_context",
    "oauth2_scheme",
]
