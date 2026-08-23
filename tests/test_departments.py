from uuid import uuid4

import pytest

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.controllers.department import DepartmentController
from app.domain.enums import EntityStatus, WorkerStatus
from app.infrastructure.db.models import Department, Project, Worker


class FakeSession:
    def __init__(self, projects: list[Project], workers: list[Worker]):
        self.projects = projects
        self.workers = workers

    async def get(self, model, object_id):
        if model is Project:
            return next((project for project in self.projects if project.id == object_id), None)
        if model is Worker:
            return next((worker for worker in self.workers if worker.id == object_id), None)
        return None

    async def commit(self):
        pass

    async def refresh(self, _department):
        pass


class FakeDepartmentRepository:
    def __init__(
        self,
        projects: list[Project],
        departments: list[Department] | None = None,
        workers: list[Worker] | None = None,
    ):
        self.projects = projects
        self.departments = departments or []
        self.workers = workers or []
        self.session = FakeSession(projects, self.workers)

    async def find_by_name(self, *, project_id, name):
        return next(
            (
                department
                for department in self.departments
                if department.project_id == project_id and department.name == name
            ),
            None,
        )

    async def get_in_organization(self, *, department_id, organization_id):
        return next(
            (
                department
                for department in self.departments
                if department.id == department_id and department.organization_id == organization_id
            ),
            None,
        )

    async def create(self, department_data):
        department = Department(id=uuid4(), **department_data)
        self.departments.append(department)
        return department

    async def update(self, department_id, update_data):
        department = next(
            department for department in self.departments if department.id == department_id
        )
        for key, value in update_data.items():
            setattr(department, key, value)
        return department

    async def list_in_project(self, **_filters):
        return [], 0


class FakeAuditRepository:
    def __init__(self):
        self.events: list[dict] = []

    async def record(self, **event):
        self.events.append(event)


def make_project(*, organization_id=None, status=EntityStatus.ACTIVE):
    return Project(
        id=uuid4(), organization_id=organization_id or uuid4(), name="Renovation", status=status
    )


def make_department(*, organization_id, project_id, name="Kitchen"):
    return Department(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        name=name,
        status=EntityStatus.ACTIVE,
    )


def make_worker(
    *,
    organization_id,
    department_id,
    full_name="Asha",
    phone_number="+14155552671",
    status=WorkerStatus.ACTIVE,
):
    return Worker(
        id=uuid4(),
        organization_id=organization_id,
        department_id=department_id,
        full_name=full_name,
        phone_number=phone_number,
        status=status,
    )


@pytest.mark.asyncio
async def test_department_creation_validates_project_tenant_and_records_audit():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    audit_repository = FakeAuditRepository()
    controller = DepartmentController(
        FakeDepartmentRepository([project]),
        audit_repository,
    )

    department = await controller.create_department(
        project_id=project.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
        name="Kitchen",
    )

    assert department.organization_id == organization_id
    assert audit_repository.events[0]["resource_type"] == "department"


@pytest.mark.asyncio
async def test_cross_tenant_project_is_hidden():
    project = make_project()
    controller = DepartmentController(FakeDepartmentRepository([project]))

    with pytest.raises(NotFoundError) as exception_info:
        await controller.create_department(
            project_id=project.id,
            organization_id=uuid4(),
            actor_user_id=uuid4(),
            name="Kitchen",
        )

    assert exception_info.value.message == f"Project '{project.id}' not found"


@pytest.mark.asyncio
async def test_department_name_is_unique_within_project():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    controller = DepartmentController(FakeDepartmentRepository([project], [department]))

    with pytest.raises(ConflictError) as exception_info:
        await controller.create_department(
            project_id=project.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            name="Kitchen",
        )

    assert exception_info.value.message == "A department with this name already exists"


@pytest.mark.asyncio
async def test_archived_project_rejects_new_departments():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id, status=EntityStatus.ARCHIVED)
    controller = DepartmentController(FakeDepartmentRepository([project]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.create_department(
            project_id=project.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            name="Kitchen",
        )

    assert exception_info.value.message == "Archived projects cannot contain new departments"


@pytest.mark.asyncio
async def test_primary_contact_worker_can_be_set_for_department_and_audited():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    worker = make_worker(organization_id=organization_id, department_id=department.id)
    audit_repository = FakeAuditRepository()
    controller = DepartmentController(
        FakeDepartmentRepository([project], [department], [worker]),
        audit_repository,
    )

    updated = await controller.update_department(
        department_id=department.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
        update_data={"primary_contact_worker_id": worker.id},
    )

    assert updated.primary_contact_worker_id == worker.id
    assert audit_repository.events[0]["metadata"]["primary_contact_worker_id"] == worker.id


@pytest.mark.asyncio
async def test_primary_contact_must_belong_to_same_department():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    other_department = make_department(
        organization_id=organization_id,
        project_id=project.id,
        name="Living Room",
    )
    worker = make_worker(organization_id=organization_id, department_id=other_department.id)
    controller = DepartmentController(FakeDepartmentRepository([project], [department], [worker]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.update_department(
            department_id=department.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            update_data={"primary_contact_worker_id": worker.id},
        )

    assert (
        exception_info.value.message == "Primary contact worker must belong to the same department"
    )


@pytest.mark.asyncio
async def test_inactive_worker_cannot_be_primary_contact():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    worker = make_worker(
        organization_id=organization_id,
        department_id=department.id,
        status=WorkerStatus.INACTIVE,
    )
    controller = DepartmentController(FakeDepartmentRepository([project], [department], [worker]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.update_department(
            department_id=department.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            update_data={"primary_contact_worker_id": worker.id},
        )

    assert exception_info.value.message == "Inactive workers cannot be primary contacts"


@pytest.mark.asyncio
async def test_archiving_department_clears_primary_contact_worker():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    worker = make_worker(organization_id=organization_id, department_id=department.id)
    department.primary_contact_worker_id = worker.id
    audit_repository = FakeAuditRepository()
    controller = DepartmentController(
        FakeDepartmentRepository([project], [department], [worker]),
        audit_repository,
    )

    await controller.archive_department(
        department_id=department.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
    )

    assert department.primary_contact_worker_id is None
    assert audit_repository.events[0]["metadata"]["primary_contact_worker_id"] is None
