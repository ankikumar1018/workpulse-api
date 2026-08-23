"""API dependency injection utilities."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.controllers.auth import AuthController
from app.controllers.organization import OrganizationController
from core.database import get_session
from core.factory import Factory


async def get_organization_controller(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationController:
    """Dependency to get organization controller with injected session."""
    return Factory.get_organization_controller(session)


async def get_auth_controller(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthController:
    """Dependency to get authentication controller with injected session."""
    return Factory.get_auth_controller(session)


# Type aliases for cleaner endpoint signatures
OrganizationCtrl = Annotated[OrganizationController, Depends(get_organization_controller)]
AuthCtrl = Annotated[AuthController, Depends(get_auth_controller)]

__all__ = [
    "AuthCtrl",
    "CurrentUser",
    "OrganizationCtrl",
    "get_auth_controller",
    "get_organization_controller",
    "get_session",
]
