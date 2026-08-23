from uuid import UUID, uuid4

import pytest

from app.controllers.organization import OrganizationController
from app.infrastructure.db.models import Organization


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


@pytest.mark.asyncio
async def test_list_organizations_is_scoped_to_authenticated_organization():
    organization_id = uuid4()
    other_organization_id = uuid4()
    organizations = [
        Organization(id=organization_id, name="Acme", slug="acme"),
        Organization(id=other_organization_id, name="Other", slug="other"),
    ]
    repository = FakeOrganizationRepository(organizations)
    controller = OrganizationController(repository)

    result, total = await controller.list_organizations(organization_id=organization_id)

    assert [organization.id for organization in result] == [organization_id]
    assert total == 1
    assert repository.requested_filters == {"id": organization_id}


def test_organization_ids_are_uuid_values():
    organization = Organization(id=uuid4(), name="Acme", slug="acme")

    assert isinstance(organization.id, UUID)
