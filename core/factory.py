"""Factory pattern for dependency injection.

This module provides a factory for creating controller instances with
injected repositories. This allows for easy testing and loose coupling.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth import AuthController
from app.controllers.organization import OrganizationController
from app.repositories.auth import AuthRepository
from app.repositories.organization import OrganizationRepository


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
        return AuthController(repository)

    # TODO: Add more controller getters as they are created
    # @staticmethod
    # def get_project_controller(session: AsyncSession) -> ProjectController:
    #     repository = ProjectRepository(session)
    #     return ProjectController(repository)


__all__ = ["Factory"]
