"""Tests for schedule configuration and lifecycle rules."""

from datetime import time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.enums import EntityStatus, ScheduleStatus
from app.infrastructure.db.models import Department, Project, Template
from app.services.schedule import ScheduleService


class FakeSession:
    def __init__(self, objects: dict[tuple[type, object], object]):
        self.objects = objects

    async def get(self, model, object_id):
        return self.objects.get((model, object_id))

    async def commit(self):
        pass

    async def refresh(self, _object):
        pass


class FakeScheduleRepository:
    def __init__(self, objects: dict[tuple[type, object], object]):
        self.session = FakeSession(objects)
        self.schedules = {}

    async def create(self, values):
        schedule_values = {"id": uuid4(), "next_run_at_utc": None, **values}
        schedule = SimpleNamespace(**schedule_values)
        self.schedules[schedule.id] = schedule
        return schedule

    async def get_in_organization(self, *, schedule_id, organization_id):
        schedule = self.schedules.get(schedule_id)
        if schedule and schedule.organization_id == organization_id:
            return schedule
        return None

    async def list_in_project(self, **_kwargs):
        return [], 0

    async def update(self, schedule_id, values):
        schedule = self.schedules.get(schedule_id)
        if schedule:
            for name, value in values.items():
                setattr(schedule, name, value)
        return schedule


def make_service():
    organization_id = uuid4()
    project_id = uuid4()
    department_id = uuid4()
    template_id = uuid4()
    project = SimpleNamespace(organization_id=organization_id, status=EntityStatus.ACTIVE)
    department = SimpleNamespace(
        organization_id=organization_id,
        project_id=project_id,
        status=EntityStatus.ACTIVE,
    )
    template = SimpleNamespace(
        organization_id=organization_id,
        project_id=project_id,
        status=EntityStatus.ACTIVE,
    )
    repository = FakeScheduleRepository(
        {
            (Project, project_id): project,
            (Department, department_id): department,
            (Template, template_id): template,
        }
    )
    return (
        ScheduleService(repository),
        repository,
        organization_id,
        project_id,
        department_id,
        template_id,
    )


@pytest.mark.asyncio
async def test_schedule_is_created_paused_and_can_be_activated_then_paused():
    service, _repository, organization_id, project_id, department_id, template_id = make_service()
    schedule = await service.create_schedule(
        organization_id=organization_id,
        actor_user_id=uuid4(),
        project_id=project_id,
        department_id=department_id,
        template_id=template_id,
        timezone="America/Los_Angeles",
        window_start_local=time(8, 0),
        window_end_local=time(17, 0),
        interval_seconds=3600,
    )

    assert schedule.status == ScheduleStatus.PAUSED
    active = await service.set_schedule_status(
        schedule_id=schedule.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
        status=ScheduleStatus.ACTIVE,
    )
    assert active.status == ScheduleStatus.ACTIVE
    assert active.next_run_at_utc is not None
    assert active.next_run_at_utc.tzinfo is not None

    paused = await service.set_schedule_status(
        schedule_id=schedule.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
        status=ScheduleStatus.PAUSED,
    )
    assert paused.status == ScheduleStatus.PAUSED
    assert paused.next_run_at_utc is None


@pytest.mark.asyncio
async def test_schedule_configuration_updates_reject_null_and_active_schedule_changes():
    service, _repository, organization_id, project_id, department_id, template_id = make_service()
    schedule = await service.create_schedule(
        organization_id=organization_id,
        actor_user_id=uuid4(),
        project_id=project_id,
        department_id=department_id,
        template_id=template_id,
        timezone="UTC",
        window_start_local=time(8, 0),
        window_end_local=time(17, 0),
        interval_seconds=3600,
    )
    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.update_schedule(
            schedule_id=schedule.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            update_data={"timezone": None},
        )
    assert "cannot be null" in exception_info.value.message

    await service.set_schedule_status(
        schedule_id=schedule.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
        status=ScheduleStatus.ACTIVE,
    )
    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.update_schedule(
            schedule_id=schedule.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            update_data={"interval_seconds": 1800},
        )
    assert "Pause a schedule" in exception_info.value.message


@pytest.mark.asyncio
async def test_schedule_rejects_unknown_timezone_and_invalid_window():
    service, _repository, organization_id, project_id, department_id, template_id = make_service()
    values = {
        "organization_id": organization_id,
        "actor_user_id": uuid4(),
        "project_id": project_id,
        "department_id": department_id,
        "template_id": template_id,
        "timezone": "Mars/Olympus",
        "window_start_local": time(8, 0),
        "window_end_local": time(17, 0),
        "interval_seconds": 3600,
    }
    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.create_schedule(**values)
    assert "Unknown timezone" in exception_info.value.message

    values["timezone"] = "UTC"
    values["window_end_local"] = time(8, 0)
    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.create_schedule(**values)
    assert "later than start" in exception_info.value.message


@pytest.mark.asyncio
async def test_schedule_rejects_cross_project_department_and_missing_tenant_scope():
    service, _repository, organization_id, project_id, department_id, template_id = make_service()
    schedule_args = {
        "organization_id": organization_id,
        "actor_user_id": uuid4(),
        "project_id": project_id,
        "department_id": department_id,
        "template_id": template_id,
        "timezone": "UTC",
        "window_start_local": time(8, 0),
        "window_end_local": time(17, 0),
        "interval_seconds": 3600,
    }

    service.repository.session.objects[(Department, department_id)].project_id = uuid4()
    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.create_schedule(**schedule_args)
    assert "Department must belong" in exception_info.value.message
    with pytest.raises(NotFoundError) as exception_info:
        await service.list_schedules(
            project_id=project_id,
            organization_id=uuid4(),
            limit=50,
            offset=0,
        )
    assert "Project" in exception_info.value.message
