"""Organization business logic/controller."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.api.errors import ConflictError, NotFoundError
from app.models.organization import Organization
from app.repositories.organization import OrganizationRepository


class OrganizationController:
    """Controller/Service for Organization business logic."""

    def __init__(self, repository: OrganizationRepository):
        """Initialize with organization repository."""
        self.repository = repository

    async def create_organization(
        self,
        name: str,
        slug: str,
    ) -> Organization:
        """Create a new organization."""
        # Check if slug already exists
        existing = await self.repository.find_by_slug(slug)
        if existing:
            raise ConflictError(f"Organization with slug '{slug}' already exists")

        # Create organization
        org_data = {
            "name": name,
            "slug": slug,
        }
        return await self.repository.create(org_data)

    async def get_organization(self, org_id: UUID) -> Organization:
        """Get organization by ID."""
        org = await self.repository.get_by_id(org_id)
        if not org:
            raise NotFoundError(f"Organization '{org_id}' not found")
        return org

    async def list_organizations(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> tuple[list[Organization], int]:
        """List organizations with optional filtering."""
        filters: dict[str, str] = {}
        if status:
            filters["status"] = status

        return await self.repository.find_all(
            limit=limit,
            offset=offset,
            **filters,
        )

    async def update_organization(
        self,
        org_id: UUID,
        update_data: dict[str, Any],
    ) -> Organization:
        """Update organization."""
        org = await self.repository.get_by_id(org_id)
        if not org:
            raise NotFoundError(f"Organization '{org_id}' not found")

        return await self.repository.update(org_id, update_data)

    async def delete_organization(self, org_id: UUID) -> None:
        """Delete organization."""
        org = await self.repository.get_by_id(org_id)
        if not org:
            raise NotFoundError(f"Organization '{org_id}' not found")

        await self.repository.delete(org_id)


__all__ = ["OrganizationController"]
