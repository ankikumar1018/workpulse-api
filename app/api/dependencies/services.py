"""Service dependency injection: builds request-scoped services via the DI factory."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.factory import Factory
from app.services.auth import AuthService
from app.services.department import DepartmentService
from app.services.message import MessageService
from app.services.organization import OrganizationService
from app.services.project import ProjectService
from app.services.template import TemplateService
from app.services.work_item import WorkItemService
from app.services.worker import WorkerService
from core.database import get_session


async def get_organization_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationService:
    """Dependency to get organization service with injected session."""
    return Factory.get_organization_service(session)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    """Dependency to get authentication service with injected session."""
    return Factory.get_auth_service(session)


async def get_project_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectService:
    """Dependency to get project service with injected session."""
    return Factory.get_project_service(session)


async def get_template_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateService:
    """Dependency to get template service with injected session."""
    return Factory.get_template_service(session)


async def get_department_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DepartmentService:
    """Dependency to get department service with injected session."""
    return Factory.get_department_service(session)


async def get_message_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageService:
    """Dependency to get message service with injected session."""
    return Factory.get_message_service(session)


async def get_worker_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkerService:
    """Dependency to get worker service with injected session."""
    return Factory.get_worker_service(session)


async def get_work_item_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkItemService:
    """Dependency to get work item service with injected session."""
    return Factory.get_work_item_service(session)


# Type aliases for cleaner endpoint signatures
OrganizationSvc = Annotated[OrganizationService, Depends(get_organization_service)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
ProjectSvc = Annotated[ProjectService, Depends(get_project_service)]
TemplateSvc = Annotated[TemplateService, Depends(get_template_service)]
DepartmentSvc = Annotated[DepartmentService, Depends(get_department_service)]
MessageSvc = Annotated[MessageService, Depends(get_message_service)]
WorkerSvc = Annotated[WorkerService, Depends(get_worker_service)]
WorkItemSvc = Annotated[WorkItemService, Depends(get_work_item_service)]

__all__ = [
    "AuthSvc",
    "DepartmentSvc",
    "MessageSvc",
    "OrganizationSvc",
    "ProjectSvc",
    "TemplateSvc",
    "WorkItemSvc",
    "WorkerSvc",
    "get_auth_service",
    "get_department_service",
    "get_message_service",
    "get_organization_service",
    "get_project_service",
    "get_template_service",
    "get_work_item_service",
    "get_worker_service",
]
