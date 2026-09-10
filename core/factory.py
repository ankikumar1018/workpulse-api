"""Factory pattern for dependency injection.

This module provides a factory for creating controller instances with
injected repositories. This allows for easy testing and loose coupling.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth import AuthController
from app.controllers.department import DepartmentController
from app.controllers.organization import OrganizationController
from app.controllers.project import ProjectController
from app.controllers.work_item import WorkItemController
from app.controllers.worker import WorkerController
from app.repositories.audit import AuditRepository
from app.repositories.auth import AuthRepository
from app.repositories.department import DepartmentRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.work_item import WorkItemRepository
from app.repositories.worker import WorkerRepository


class Factory:
    """Factory for creating controller instances with injected dependencies."""

    @staticmethod
    def get_organization_controller(session: AsyncSession) -> OrganizationController:
        """Get organization controller with injected repository."""
        repository = OrganizationRepository(session)
        return OrganizationController(repository)

    @staticmethod
    def get_auth_controller(session: AsyncSession) -> AuthController:
        """Get authentication controller with injected repository."""
        repository = AuthRepository(session)
        audit_repository = AuditRepository(session)
        return AuthController(repository, audit_repository)

    @staticmethod
    def get_project_controller(session: AsyncSession) -> ProjectController:
        """Get project controller with injected repositories."""
        repository = ProjectRepository(session)
        audit_repository = AuditRepository(session)
        return ProjectController(repository, audit_repository)

    @staticmethod
    def get_department_controller(session: AsyncSession) -> DepartmentController:
        """Get department controller with injected repositories."""
        repository = DepartmentRepository(session)
        audit_repository = AuditRepository(session)
        return DepartmentController(repository, audit_repository)

    @staticmethod
    def get_worker_controller(session: AsyncSession) -> WorkerController:
        """Get worker controller with injected repositories."""
        repository = WorkerRepository(session)
        audit_repository = AuditRepository(session)
        return WorkerController(repository, audit_repository)

    @staticmethod
    def get_work_item_controller(session: AsyncSession) -> WorkItemController:
        """Get work item controller with injected repositories."""
        repository = WorkItemRepository(session)
        audit_repository = AuditRepository(session)
        return WorkItemController(repository, audit_repository)


__all__ = ["Factory"]
