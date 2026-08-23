"""API dependency injection and authorization."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from app.api.errors import ForbiddenError


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


async def get_auth_context(
    authorization: str | None = Header(None),
) -> AuthContext:
    """
    Extract and validate JWT token from Authorization header.

    TODO: Implement full JWT verification in WI-2.1.
    For now, this is a stub that allows local development.
    """
    if not authorization or not authorization.startswith("Bearer "):
        # In development, allow requests without token to test endpoints
        # Production: raise UnauthorizedError("Missing authorization header")
        import uuid
        return AuthContext(
            user_id=uuid.uuid7(),
            organization_id=uuid.uuid7(),
            role="admin",
        )

    # TODO: Decode and validate JWT token
    # For now, accept any bearer token
    import uuid
    return AuthContext(
        user_id=uuid.uuid7(),
        organization_id=uuid.uuid7(),
        role="admin",
    )


# Type alias for dependency injection
CurrentUser = Annotated[AuthContext, Depends(get_auth_context)]


__all__ = [
    "AuthContext",
    "CurrentUser",
    "get_auth_context",
]
