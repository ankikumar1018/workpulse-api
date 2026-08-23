from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.controllers.project import ProjectController
from app.domain.enums import EntityStatus
from app.infrastructure.db.models import Project
from app.schemas.requests.project import ProjectCreateRequest, ProjectUpdateRequest


class FakeSession:
    async def commit(self):
        pass

    async def refresh(self, _project):
        pass


class FakeProjectRepository:
    def __init__(self, projects: list[Project]):
        self.projects = projects
        self.session = FakeSession()

    async def find_by_name(self, *, organization_id, name):
        return next(
            (
                project
                for project in self.projects
                if project.organization_id == organization_id and project.name == name
            ),
            None,
        )

    async def get_in_organization(self, *, project_id, organization_id):
        return next(
            (
                project
                for project in self.projects
                if project.id == project_id and project.organization_id == organization_id
            ),
            None,
        )

    async def create(self, project_data):
        project = Project(id=uuid4(), **project_data)
        self.projects.append(project)
        return project

    async def update(self, project_id, update_data):
        project = next(project for project in self.projects if project.id == project_id)
        for key, value in update_data.items():
            setattr(project, key, value)
        return project

    async def list_in_organization(self, **_filters):
        return [], 0


class FakeAuditRepository:
    def __init__(self):
        self.events: list[dict] = []

    async def record(self, **event):
        self.events.append(event)


def make_project(*, organization_id=None, name="Kitchen"):
    return Project(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        name=name,
        status=EntityStatus.ACTIVE,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )


@pytest.mark.asyncio
async def test_project_lifecycle_is_tenant_scoped_and_audited():
    organization_id = uuid4()
    actor_user_id = uuid4()
    repository = FakeProjectRepository([make_project(organization_id=uuid4(), name="Other")])
    audit_repository = FakeAuditRepository()
    controller = ProjectController(repository, audit_repository)

    project = await controller.create_project(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        name="Kitchen",
        description="Renovation",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
    )

    assert project.organization_id == organization_id
    with pytest.raises(NotFoundError) as exception_info:
        await controller.get_project(project_id=project.id, organization_id=uuid4())
    assert exception_info.value.message == f"Project '{project.id}' not found"
    assert audit_repository.events[0]["organization_id"] == organization_id
    assert audit_repository.events[0]["actor_user_id"] == actor_user_id


@pytest.mark.asyncio
async def test_project_duplicate_name_is_rejected_within_organization():
    organization_id = uuid4()
    repository = FakeProjectRepository([make_project(organization_id=organization_id)])
    controller = ProjectController(repository)

    with pytest.raises(ConflictError) as exception_info:
        await controller.create_project(
            organization_id=organization_id,
            actor_user_id=uuid4(),
            name="Kitchen",
            description=None,
            start_date=None,
            end_date=None,
        )
    assert exception_info.value.message == "A project with this name already exists"


@pytest.mark.asyncio
async def test_archived_project_cannot_be_modified():
    project = make_project()
    project.status = EntityStatus.ARCHIVED
    controller = ProjectController(FakeProjectRepository([project]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.update_project(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_user_id=uuid4(),
            update_data={"name": "New name"},
        )
    assert exception_info.value.message == "Archived projects cannot be modified"


@pytest.mark.asyncio
async def test_partial_project_date_update_uses_existing_date_for_validation():
    project = make_project()
    controller = ProjectController(FakeProjectRepository([project]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.update_project(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_user_id=uuid4(),
            update_data={"start_date": date(2026, 2, 1)},
        )

    assert exception_info.value.message == "end_date must be on or after start_date"


def test_project_request_date_range_is_validated():
    with pytest.raises(ValidationError, match="end_date must be on or after start_date"):
        ProjectCreateRequest(
            name="Kitchen",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 31),
        )

    with pytest.raises(ValidationError, match="end_date must be on or after start_date"):
        ProjectUpdateRequest(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 31),
        )
