"""Factory pattern for dependency injection.

This module provides a factory for creating service instances with
injected repositories. This allows for easy testing and loose coupling.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit import AuditRepository
from app.repositories.auth import AuthRepository
from app.repositories.department import DepartmentRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.work_item import WorkItemRepository
from app.repositories.worker import WorkerRepository
from app.services.auth import AuthService
from app.services.department import DepartmentService
from app.services.organization import OrganizationService
from app.services.project import ProjectService
from app.services.work_item import WorkItemService
from app.services.worker import WorkerService


class Factory:
    """Factory for creating service instances with injected dependencies."""

    @staticmethod
    def get_organization_service(session: AsyncSession) -> OrganizationService:
        """Get organization service with injected repository."""
        repository = OrganizationRepository(session)
        return OrganizationService(repository)

    @staticmethod
    def get_auth_service(session: AsyncSession) -> AuthService:
        """Get authentication service with injected repository."""
        repository = AuthRepository(session)
        audit_repository = AuditRepository(session)
        return AuthService(repository, audit_repository)

    @staticmethod
    def get_project_service(session: AsyncSession) -> ProjectService:
        """Get project service with injected repositories."""
        repository = ProjectRepository(session)
        audit_repository = AuditRepository(session)
        return ProjectService(repository, audit_repository)

    @staticmethod
    def get_department_service(session: AsyncSession) -> DepartmentService:
        """Get department service with injected repositories."""
        repository = DepartmentRepository(session)
        audit_repository = AuditRepository(session)
        return DepartmentService(repository, audit_repository)

    @staticmethod
    def get_worker_service(session: AsyncSession) -> WorkerService:
        """Get worker service with injected repositories."""
        repository = WorkerRepository(session)
        audit_repository = AuditRepository(session)
        return WorkerService(repository, audit_repository)

    @staticmethod
    def get_work_item_service(session: AsyncSession) -> WorkItemService:
        """Get work item service with injected repositories."""
        repository = WorkItemRepository(session)
        audit_repository = AuditRepository(session)
        return WorkItemService(repository, audit_repository)


__all__ = ["Factory"]
