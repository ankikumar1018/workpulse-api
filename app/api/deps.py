"""API dependency injection utilities."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.controllers.auth import AuthController
from app.controllers.department import DepartmentController
from app.controllers.organization import OrganizationController
from app.controllers.project import ProjectController
from app.controllers.worker import WorkerController
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


async def get_project_controller(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectController:
    """Dependency to get project controller with injected session."""
    return Factory.get_project_controller(session)


async def get_department_controller(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DepartmentController:
    """Dependency to get department controller with injected session."""
    return Factory.get_department_controller(session)


async def get_worker_controller(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkerController:
    """Dependency to get worker controller with injected session."""
    return Factory.get_worker_controller(session)


# Type aliases for cleaner endpoint signatures
OrganizationCtrl = Annotated[OrganizationController, Depends(get_organization_controller)]
AuthCtrl = Annotated[AuthController, Depends(get_auth_controller)]
ProjectCtrl = Annotated[ProjectController, Depends(get_project_controller)]
DepartmentCtrl = Annotated[DepartmentController, Depends(get_department_controller)]
WorkerCtrl = Annotated[WorkerController, Depends(get_worker_controller)]

__all__ = [
    "AuthCtrl",
    "CurrentUser",
    "DepartmentCtrl",
    "OrganizationCtrl",
    "ProjectCtrl",
    "WorkerCtrl",
    "get_auth_controller",
    "get_department_controller",
    "get_organization_controller",
    "get_project_controller",
    "get_session",
    "get_worker_controller",
]
