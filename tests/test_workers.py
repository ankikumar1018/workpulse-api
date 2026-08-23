from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.controllers.worker import WorkerController
from app.domain.enums import ConsentStatus, EntityStatus
from app.infrastructure.db.models import Department, Project, Worker
from app.schemas.requests.worker import WorkerCreateRequest


class FakeSession:
    def __init__(self, projects: list[Project], departments: list[Department]):
        self.projects = projects
        self.departments = departments

    async def get(self, model, object_id):
        records = self.projects if model is Project else self.departments
        return next((record for record in records if record.id == object_id), None)

    async def commit(self):
        pass

    async def refresh(self, _worker):
        pass


class FakeWorkerRepository:
    def __init__(
        self,
        projects: list[Project],
        departments: list[Department],
        workers: list[Worker] | None = None,
    ):
        self.projects = projects
        self.departments = departments
        self.workers = workers or []
        self.session = FakeSession(projects, departments)

    async def find_by_phone(self, *, organization_id, phone_number):
        return next(
            (
                worker
                for worker in self.workers
                if worker.organization_id == organization_id and worker.phone_number == phone_number
            ),
            None,
        )

    async def get_in_organization(self, *, worker_id, organization_id):
        return next(
            (
                worker
                for worker in self.workers
                if worker.id == worker_id and worker.organization_id == organization_id
            ),
            None,
        )

    async def create(self, worker_data):
        worker = Worker(id=uuid4(), **worker_data)
        self.workers.append(worker)
        return worker

    async def update(self, worker_id, update_data):
        worker = next(worker for worker in self.workers if worker.id == worker_id)
        for key, value in update_data.items():
            setattr(worker, key, value)
        return worker

    async def list_in_department(self, **_filters):
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


def make_department(*, organization_id, project_id, name="Kitchen", status=EntityStatus.ACTIVE):
    return Department(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        name=name,
        status=status,
    )


@pytest.mark.asyncio
async def test_worker_creation_is_scoped_and_audited():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    audit_repository = FakeAuditRepository()
    controller = WorkerController(
        FakeWorkerRepository([project], [department]),
        audit_repository,
    )

    worker = await controller.create_worker(
        department_id=department.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
        full_name="Asha Designer",
        phone_number="+14155552671",
        contact_channel="whatsapp",
        consent_status="opted_in",
    )

    assert worker.organization_id == organization_id
    assert worker.department_id == department.id
    assert worker.contact_channel.value == "whatsapp"
    assert worker.consent_status.value == "opted_in"
    assert audit_repository.events[0]["resource_type"] == "worker"


@pytest.mark.asyncio
async def test_worker_creation_rejects_cross_tenant_department():
    project = make_project()
    department = make_department(organization_id=project.organization_id, project_id=project.id)
    controller = WorkerController(FakeWorkerRepository([project], [department]))

    with pytest.raises(NotFoundError) as exception_info:
        await controller.create_worker(
            department_id=department.id,
            organization_id=uuid4(),
            actor_user_id=uuid4(),
            full_name="Asha Designer",
            phone_number="+14155552671",
            contact_channel="whatsapp",
            consent_status="opted_in",
        )

    assert exception_info.value.message == f"Department '{department.id}' not found"


@pytest.mark.asyncio
async def test_worker_phone_is_unique_within_organization():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    existing = Worker(
        id=uuid4(),
        organization_id=organization_id,
        department_id=department.id,
        full_name="Existing Worker",
        phone_number="+14155552671",
        status="active",
    )
    controller = WorkerController(FakeWorkerRepository([project], [department], [existing]))

    with pytest.raises(ConflictError) as exception_info:
        await controller.create_worker(
            department_id=department.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            full_name="Asha Designer",
            phone_number="+14155552671",
            contact_channel="whatsapp",
            consent_status="opted_in",
        )

    assert exception_info.value.message == "A worker with this phone number already exists"


@pytest.mark.asyncio
async def test_archived_department_rejects_new_workers():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(
        organization_id=organization_id,
        project_id=project.id,
        status=EntityStatus.ARCHIVED,
    )
    controller = WorkerController(FakeWorkerRepository([project], [department]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.create_worker(
            department_id=department.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            full_name="Asha Designer",
            phone_number="+14155552671",
            contact_channel="whatsapp",
            consent_status="opted_in",
        )

    assert exception_info.value.message == "Archived departments cannot contain workers"


@pytest.mark.asyncio
async def test_worker_assignment_can_move_active_worker_and_records_audit():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    source_department = make_department(
        organization_id=organization_id,
        project_id=project.id,
        name="Kitchen",
    )
    target_department = make_department(
        organization_id=organization_id,
        project_id=project.id,
        name="Living Room",
    )
    worker = Worker(
        id=uuid4(),
        organization_id=organization_id,
        department_id=source_department.id,
        full_name="Asha Designer",
        phone_number="+14155552671",
        status="active",
    )
    audit_repository = FakeAuditRepository()
    controller = WorkerController(
        FakeWorkerRepository([project], [source_department, target_department], [worker]),
        audit_repository,
    )

    updated = await controller.assign_worker_to_department(
        worker_id=worker.id,
        department_id=target_department.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
    )

    assert updated.department_id == target_department.id
    assert audit_repository.events[0]["metadata"]["assignment_action"] == "assigned"


@pytest.mark.asyncio
async def test_inactive_worker_cannot_be_assigned():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    source_department = make_department(organization_id=organization_id, project_id=project.id)
    target_department = make_department(
        organization_id=organization_id,
        project_id=project.id,
        name="Living Room",
    )
    worker = Worker(
        id=uuid4(),
        organization_id=organization_id,
        department_id=source_department.id,
        full_name="Asha Designer",
        phone_number="+14155552671",
        status="inactive",
    )
    controller = WorkerController(
        FakeWorkerRepository([project], [source_department, target_department], [worker])
    )

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.assign_worker_to_department(
            worker_id=worker.id,
            department_id=target_department.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
        )

    assert exception_info.value.message == "Inactive workers cannot be communication recipients"


@pytest.mark.asyncio
async def test_opted_out_worker_cannot_be_assigned():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    source_department = make_department(organization_id=organization_id, project_id=project.id)
    target_department = make_department(
        organization_id=organization_id,
        project_id=project.id,
        name="Living Room",
    )
    worker = Worker(
        id=uuid4(),
        organization_id=organization_id,
        department_id=source_department.id,
        full_name="Asha Designer",
        phone_number="+14155552671",
        consent_status=ConsentStatus.OPTED_OUT,
        status="active",
    )
    controller = WorkerController(
        FakeWorkerRepository([project], [source_department, target_department], [worker])
    )

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.assign_worker_to_department(
            worker_id=worker.id,
            department_id=target_department.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
        )

    assert exception_info.value.message == "Opted-out workers cannot be communication recipients"


@pytest.mark.asyncio
async def test_worker_assignment_can_be_removed_and_worker_becomes_inactive():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    department = make_department(organization_id=organization_id, project_id=project.id)
    worker = Worker(
        id=uuid4(),
        organization_id=organization_id,
        department_id=department.id,
        full_name="Asha Designer",
        phone_number="+14155552671",
        status="active",
    )
    audit_repository = FakeAuditRepository()
    controller = WorkerController(
        FakeWorkerRepository([project], [department], [worker]),
        audit_repository,
    )

    await controller.remove_worker_assignment(
        worker_id=worker.id,
        department_id=department.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
    )

    assert worker.status == "inactive"
    assert audit_repository.events[0]["metadata"]["assignment_action"] == "removed"


@pytest.mark.asyncio
async def test_worker_assignment_removal_rejects_mismatched_department():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    source_department = make_department(organization_id=organization_id, project_id=project.id)
    another_department = make_department(
        organization_id=organization_id,
        project_id=project.id,
        name="Living Room",
    )
    worker = Worker(
        id=uuid4(),
        organization_id=organization_id,
        department_id=source_department.id,
        full_name="Asha Designer",
        phone_number="+14155552671",
        status="active",
    )
    controller = WorkerController(
        FakeWorkerRepository([project], [source_department, another_department], [worker])
    )

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await controller.remove_worker_assignment(
            worker_id=worker.id,
            department_id=another_department.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
        )

    assert exception_info.value.message == "Worker is not assigned to this department"


def test_worker_request_validates_e164_phone_number():
    with pytest.raises(ValidationError):
        WorkerCreateRequest(full_name="Asha Designer", phone_number="invalid-number")


def test_worker_request_normalizes_phone_number():
    request = WorkerCreateRequest(
        full_name="Asha Designer",
        phone_number="+1 (415) 555-2671",
    )

    assert request.phone_number == "+14155552671"
