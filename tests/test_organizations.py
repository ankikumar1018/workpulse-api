from uuid import UUID, uuid4

import pytest

from app.api.errors import ConflictError, NotFoundError
from app.infrastructure.db.models import Organization
from app.services.organization import OrganizationService


class FakeOrganizationRepository:
    def __init__(self, organizations: list[Organization]):
        self.organizations = organizations
        self.requested_filters: dict[str, object] | None = None

    async def find_all(self, *, limit: int, offset: int, **filters):
        self.requested_filters = filters
        matches = [
            organization
            for organization in self.organizations
            if all(getattr(organization, key) == value for key, value in filters.items())
        ]
        return matches[offset : offset + limit], len(matches)

    async def find_by_slug(self, slug: str):
        return next(
            (organization for organization in self.organizations if organization.slug == slug), None
        )

    async def create(self, organization_data):
        organization = Organization(id=uuid4(), **organization_data)
        self.organizations.append(organization)
        return organization

    async def get_by_id(self, org_id):
        return next(
            (organization for organization in self.organizations if organization.id == org_id), None
        )

    async def update(self, org_id, update_data):
        organization = await self.get_by_id(org_id)
        if organization is None:
            return None
        for field, value in update_data.items():
            setattr(organization, field, value)
        return organization

    async def delete(self, org_id):
        self.organizations[:] = [
            organization for organization in self.organizations if organization.id != org_id
        ]


@pytest.mark.asyncio
async def test_list_organizations_is_scoped_to_authenticated_organization():
    organization_id = uuid4()
    other_organization_id = uuid4()
    organizations = [
        Organization(id=organization_id, name="Acme", slug="acme"),
        Organization(id=other_organization_id, name="Other", slug="other"),
    ]
    repository = FakeOrganizationRepository(organizations)
    controller = OrganizationService(repository)

    result, total = await controller.list_organizations(organization_id=organization_id)

    assert [organization.id for organization in result] == [organization_id]
    assert total == 1
    assert repository.requested_filters == {"id": organization_id}


def test_organization_ids_are_uuid_values():
    organization = Organization(id=uuid4(), name="Acme", slug="acme")

    assert isinstance(organization.id, UUID)


@pytest.mark.asyncio
async def test_organization_service_crud_and_duplicate_slug_validation():
    repository = FakeOrganizationRepository([])
    service = OrganizationService(repository)

    organization = await service.create_organization(name="Northstar", slug="northstar")
    assert organization.name == "Northstar"
    assert await service.get_organization(organization.id) is organization

    with pytest.raises(ConflictError) as conflict_error:
        await service.create_organization(name="Duplicate", slug="northstar")
    assert "already exists" in conflict_error.value.message

    updated = await service.update_organization(organization.id, {"name": "Northstar Studio"})
    assert updated.name == "Northstar Studio"

    await service.delete_organization(organization.id)
    with pytest.raises(NotFoundError) as missing_error:
        await service.get_organization(organization.id)
    assert "not found" in missing_error.value.message
