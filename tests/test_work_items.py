"""Comprehensive tests for work item domain model and state transitions."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import AuthContext, get_auth_context, get_work_item_service
from app.api.errors import UnprocessableEntityError
from app.domain.enums import EntityStatus, WorkerStatus, WorkPriority, WorkStatus
from app.domain.work_item import InvalidTransitionError, WorkItem, WorkItemStateTransition
from app.infrastructure.db.models import Department, Project, Worker, WorkItem as WorkItemModel
from app.main import app
from app.services.work_item import WorkItemService


class FakeWorkItemStatusHistoryRepository:
    """In-memory repository used to test work-item status history persistence."""

    def __init__(self):
        self.records: list[dict] = []

    async def record(self, **payload):
        payload.setdefault("created_at", datetime.now(UTC))
        self.records.append(payload)
        return payload

    async def list_for_work_item(self, *, work_item_id, organization_id, limit=100, offset=0):
        items = [
            record
            for record in self.records
            if record["work_item_id"] == work_item_id
            and record["organization_id"] == organization_id
        ]
        return items[offset : offset + limit], len(items)


class FakeWorkItemServiceSession:
    def __init__(self, objects):
        self.objects = objects
        self.flush_count = 0
        self.commit_count = 0

    async def get(self, model, object_id):
        return self.objects.get((model, object_id))

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, item):
        return item


class FakeWorkItemServiceRepository:
    def __init__(self, objects):
        self.session = FakeWorkItemServiceSession(objects)
        self.items = {}
        self.create_data = None
        self.list_filters = None

    async def create(self, data):
        self.create_data = data
        item = SimpleNamespace(id=uuid4(), **data)
        self.items[item.id] = item
        return item

    async def get_in_organization(self, *, work_item_id, organization_id):
        item = self.items.get(work_item_id)
        return item if item and item.organization_id == organization_id else None

    async def list_in_project(self, **filters):
        self.list_filters = filters
        return [], 0


class FakeWorkItemAuditRepository:
    def __init__(self):
        self.events = []

    async def record(self, **event):
        self.events.append(event)


def make_work_item_service(
    *,
    project_status=EntityStatus.ACTIVE,
    department_status=EntityStatus.ACTIVE,
    worker_status=WorkerStatus.ACTIVE,
    department_project_id=None,
    worker_department_id=None,
):
    organization_id = uuid4()
    project_id = uuid4()
    department_id = uuid4()
    worker_id = uuid4()
    project = SimpleNamespace(organization_id=organization_id, status=project_status)
    department = SimpleNamespace(
        organization_id=organization_id,
        project_id=department_project_id or project_id,
        status=department_status,
    )
    worker = SimpleNamespace(
        organization_id=organization_id,
        department_id=worker_department_id or department_id,
        status=worker_status,
    )
    repository = FakeWorkItemServiceRepository(
        {
            (Project, project_id): project,
            (Department, department_id): department,
            (Worker, worker_id): worker,
        }
    )
    audit_repository = FakeWorkItemAuditRepository()
    history_repository = FakeWorkItemStatusHistoryRepository()
    service = WorkItemService(repository, audit_repository, history_repository)
    scope = {
        "organization_id": organization_id,
        "project_id": project_id,
        "department_id": department_id,
        "worker_id": worker_id,
    }
    return service, repository, audit_repository, history_repository, scope


class TestWorkItemStateTransition:
    """Test the state transition rules for work items."""

    def test_valid_transitions_from_open(self):
        """Test valid transitions from OPEN status."""
        assert WorkItemStateTransition.is_valid_transition(WorkStatus.OPEN, WorkStatus.IN_PROGRESS)
        assert WorkItemStateTransition.is_valid_transition(WorkStatus.OPEN, WorkStatus.BLOCKED)
        assert WorkItemStateTransition.is_valid_transition(WorkStatus.OPEN, WorkStatus.CANCELLED)

    def test_invalid_transitions_from_open(self):
        """Test invalid transitions from OPEN status."""
        assert not WorkItemStateTransition.is_valid_transition(WorkStatus.OPEN, WorkStatus.DONE)
        # No self-transitions in the VALID_TRANSITIONS definition, but they should be allowed
        assert not WorkItemStateTransition.is_valid_transition(WorkStatus.OPEN, WorkStatus.OPEN)

    def test_valid_transitions_from_in_progress(self):
        """Test valid transitions from IN_PROGRESS status."""
        assert WorkItemStateTransition.is_valid_transition(
            WorkStatus.IN_PROGRESS, WorkStatus.BLOCKED
        )
        assert WorkItemStateTransition.is_valid_transition(WorkStatus.IN_PROGRESS, WorkStatus.DONE)
        assert WorkItemStateTransition.is_valid_transition(
            WorkStatus.IN_PROGRESS, WorkStatus.CANCELLED
        )

    def test_invalid_transitions_from_in_progress(self):
        """Test invalid transitions from IN_PROGRESS status."""
        assert not WorkItemStateTransition.is_valid_transition(
            WorkStatus.IN_PROGRESS, WorkStatus.OPEN
        )

    def test_valid_transitions_from_blocked(self):
        """Test valid transitions from BLOCKED status."""
        assert WorkItemStateTransition.is_valid_transition(
            WorkStatus.BLOCKED, WorkStatus.IN_PROGRESS
        )
        assert WorkItemStateTransition.is_valid_transition(WorkStatus.BLOCKED, WorkStatus.OPEN)
        assert WorkItemStateTransition.is_valid_transition(WorkStatus.BLOCKED, WorkStatus.CANCELLED)

    def test_invalid_transitions_from_blocked(self):
        """Test invalid transitions from BLOCKED status."""
        assert not WorkItemStateTransition.is_valid_transition(WorkStatus.BLOCKED, WorkStatus.DONE)

    def test_terminal_states_no_transitions(self):
        """Test that terminal states (DONE and CANCELLED) have no outgoing transitions."""
        assert not WorkItemStateTransition.is_valid_transition(WorkStatus.DONE, WorkStatus.OPEN)
        assert not WorkItemStateTransition.is_valid_transition(
            WorkStatus.DONE, WorkStatus.IN_PROGRESS
        )
        assert not WorkItemStateTransition.is_valid_transition(
            WorkStatus.CANCELLED, WorkStatus.OPEN
        )
        assert not WorkItemStateTransition.is_valid_transition(
            WorkStatus.CANCELLED, WorkStatus.IN_PROGRESS
        )

    def test_validate_transition_valid(self):
        """Test validate_transition with valid transitions."""
        # Should not raise
        WorkItemStateTransition.validate_transition(WorkStatus.OPEN, WorkStatus.IN_PROGRESS)
        WorkItemStateTransition.validate_transition(WorkStatus.IN_PROGRESS, WorkStatus.DONE)

    def test_validate_transition_invalid(self):
        """Test validate_transition with invalid transitions."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            WorkItemStateTransition.validate_transition(WorkStatus.OPEN, WorkStatus.DONE)
        assert "Cannot transition" in str(exc_info.value)
        assert "open" in str(exc_info.value)
        assert "done" in str(exc_info.value)

    def test_validate_transition_same_status(self):
        """Test that transitioning to the same status is allowed (idempotent)."""
        # Should not raise - same status transitions are idempotent
        WorkItemStateTransition.validate_transition(WorkStatus.OPEN, WorkStatus.OPEN)
        WorkItemStateTransition.validate_transition(WorkStatus.DONE, WorkStatus.DONE)

    def test_get_allowed_transitions(self):
        """Test getting allowed transitions from a status."""
        open_transitions = WorkItemStateTransition.get_allowed_transitions(WorkStatus.OPEN)
        assert open_transitions == {
            WorkStatus.IN_PROGRESS,
            WorkStatus.BLOCKED,
            WorkStatus.CANCELLED,
        }

        done_transitions = WorkItemStateTransition.get_allowed_transitions(WorkStatus.DONE)
        assert done_transitions == set()

        blocked_transitions = WorkItemStateTransition.get_allowed_transitions(WorkStatus.BLOCKED)
        assert blocked_transitions == {
            WorkStatus.IN_PROGRESS,
            WorkStatus.OPEN,
            WorkStatus.CANCELLED,
        }


class TestWorkItemEntity:
    """Test the WorkItem domain entity."""

    def test_work_item_initialization(self):
        """Test creating a work item entity."""
        from uuid import uuid4

        work_item_id = uuid4()
        org_id = uuid4()
        proj_id = uuid4()
        dept_id = uuid4()

        work_item = WorkItem(
            id=work_item_id,
            organization_id=org_id,
            project_id=proj_id,
            department_id=dept_id,
            status=WorkStatus.OPEN,
        )

        assert work_item.id == work_item_id
        assert work_item.organization_id == org_id
        assert work_item.project_id == proj_id
        assert work_item.department_id == dept_id
        assert work_item.status == WorkStatus.OPEN

    def test_can_transition_to(self):
        """Test checking if transition is allowed."""
        from uuid import uuid4

        work_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.OPEN,
        )

        assert work_item.can_transition_to(WorkStatus.IN_PROGRESS)
        assert work_item.can_transition_to(WorkStatus.BLOCKED)
        assert work_item.can_transition_to(WorkStatus.CANCELLED)
        assert not work_item.can_transition_to(WorkStatus.DONE)

    def test_transition_to_valid(self):
        """Test transitioning to a valid status."""
        from uuid import uuid4

        work_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.OPEN,
        )

        work_item.transition_to(WorkStatus.IN_PROGRESS)
        assert work_item.status == WorkStatus.IN_PROGRESS

    def test_transition_to_invalid(self):
        """Test transitioning to an invalid status raises error."""
        from uuid import uuid4

        work_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.OPEN,
        )

        with pytest.raises(InvalidTransitionError):
            work_item.transition_to(WorkStatus.DONE)

    def test_transition_chain(self):
        """Test a chain of valid transitions."""
        from uuid import uuid4

        work_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.OPEN,
        )

        # OPEN -> IN_PROGRESS -> DONE
        work_item.transition_to(WorkStatus.IN_PROGRESS)
        assert work_item.status == WorkStatus.IN_PROGRESS

        work_item.transition_to(WorkStatus.DONE)
        assert work_item.status == WorkStatus.DONE

        # DONE is terminal
        with pytest.raises(InvalidTransitionError):
            work_item.transition_to(WorkStatus.OPEN)

    def test_get_allowed_transitions(self):
        """Test getting allowed transitions from work item."""
        from uuid import uuid4

        work_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.BLOCKED,
        )

        allowed = work_item.get_allowed_transitions()
        assert allowed == {WorkStatus.IN_PROGRESS, WorkStatus.OPEN, WorkStatus.CANCELLED}

    def test_is_terminal(self):
        """Test checking if status is terminal."""
        from uuid import uuid4

        done_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.DONE,
        )
        assert done_item.is_terminal()

        open_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.OPEN,
        )
        assert not open_item.is_terminal()

    def test_blocked_to_open_to_in_progress(self):
        """Test a complex transition path: BLOCKED -> OPEN -> IN_PROGRESS."""
        from uuid import uuid4

        work_item = WorkItem(
            id=uuid4(),
            organization_id=uuid4(),
            project_id=uuid4(),
            department_id=uuid4(),
            status=WorkStatus.BLOCKED,
        )

        work_item.transition_to(WorkStatus.OPEN)
        assert work_item.status == WorkStatus.OPEN

        work_item.transition_to(WorkStatus.IN_PROGRESS)
        assert work_item.status == WorkStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_work_item_status_update_records_history():
    """Transitions should persist an append-only status timeline for each work item."""
    work_item_id = uuid4()
    organization_id = uuid4()
    actor_user_id = uuid4()

    work_item = WorkItemModel(
        id=work_item_id,
        organization_id=organization_id,
        project_id=uuid4(),
        department_id=uuid4(),
        title="Install kitchen cabinets",
        status=WorkStatus.OPEN,
    )

    class FakeSession:
        async def flush(self):
            return None

    class FakeWorkItemRepository:
        def __init__(self):
            self.session = FakeSession()
            self.entity = work_item

        async def get_in_organization(self, *, work_item_id, organization_id):
            if self.entity.id == work_item_id and self.entity.organization_id == organization_id:
                return self.entity
            return None

    history_repo = FakeWorkItemStatusHistoryRepository()

    from app.services.work_item import WorkItemService

    controller = WorkItemService(
        FakeWorkItemRepository(),
        status_history_repository=history_repo,
    )

    result = await controller.update_work_item_status(
        work_item_id=work_item_id,
        new_status="in_progress",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        reason="Work started",
    )

    assert result.status == WorkStatus.IN_PROGRESS
    assert history_repo.records[0]["work_item_id"] == work_item_id
    assert history_repo.records[0]["organization_id"] == organization_id
    assert history_repo.records[0]["previous_status"] == WorkStatus.OPEN
    assert history_repo.records[0]["new_status"] == WorkStatus.IN_PROGRESS
    assert history_repo.records[0]["actor_user_id"] == actor_user_id
    assert history_repo.records[0]["reason"] == "Work started"
    assert history_repo.records[0]["created_at"] is not None


@pytest.mark.asyncio
async def test_work_item_service_list_filters_priority_and_overdue():
    """List endpoints should support filtering by priority and overdue status."""
    organization_id = uuid4()
    project_id = uuid4()

    class FakeProject:
        def __init__(self):
            self.organization_id = organization_id
            self.status = "active"

    class FakeSession:
        async def get(self, model, obj_id):
            if model.__name__ == "Project" and obj_id == project_id:
                return FakeProject()
            return None

    class FakeWorkItemRepository:
        def __init__(self):
            self.session = FakeSession()
            self.calls = []

        async def list_in_project(self, **kwargs):
            self.calls.append(kwargs)
            return [], 0

    repo = FakeWorkItemRepository()
    from app.services.work_item import WorkItemService

    controller = WorkItemService(repo)

    await controller.list_work_items(
        project_id=project_id,
        organization_id=organization_id,
        limit=20,
        offset=0,
        priority="high",
        search="review",
        overdue=True,
    )

    assert repo.calls[0]["priority"] == "high"
    assert repo.calls[0]["search"] == "review"
    assert repo.calls[0]["overdue"] is True


def test_work_item_search_query_is_forwarded_with_tenant_scope_and_pagination():
    organization_id = uuid4()
    project_id = uuid4()
    list_calls: list[dict] = []

    class FakeWorkItemService:
        async def list_work_items(self, **kwargs):
            list_calls.append(kwargs)
            return [], 240

    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id=uuid4(), organization_id=organization_id
    )
    app.dependency_overrides[get_work_item_service] = lambda: FakeWorkItemService()
    client = TestClient(app)
    try:
        response = client.get(
            f"/api/v1/projects/{project_id}/work_items?search=follow-up&limit=50&offset=100"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "total": 240,
        "limit": 50,
        "offset": 100,
        "hasMore": True,
    }
    assert list_calls[0]["organization_id"] == organization_id
    assert list_calls[0]["project_id"] == project_id
    assert list_calls[0]["search"] == "follow-up"


@pytest.mark.asyncio
async def test_work_item_service_creation_records_scope_and_audit_metadata():
    service, repository, audit_repository, _, scope = make_work_item_service()
    actor_user_id = uuid4()
    due_at = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)

    item = await service.create_work_item(
        project_id=scope["project_id"],
        department_id=scope["department_id"],
        organization_id=scope["organization_id"],
        actor_user_id=actor_user_id,
        title="Review onboarding queue",
        description="Check outstanding tasks",
        priority="high",
        worker_id=scope["worker_id"],
        due_at=due_at,
    )

    assert item.organization_id == scope["organization_id"]
    assert item.project_id == scope["project_id"]
    assert item.department_id == scope["department_id"]
    assert item.worker_id == scope["worker_id"]
    assert item.priority == WorkPriority.HIGH
    assert item.status == WorkStatus.OPEN
    assert item.due_at == due_at
    assert repository.create_data["created_by_user_id"] == actor_user_id
    assert audit_repository.events[0]["action"].value == "create"
    assert audit_repository.events[0]["metadata"]["project_id"] == str(scope["project_id"])


@pytest.mark.parametrize(
    "project_status, department_status, worker_status, wrong_project, wrong_department, priority, expected_error",
    [
        pytest.param(
            EntityStatus.ARCHIVED,
            EntityStatus.ACTIVE,
            WorkerStatus.ACTIVE,
            False,
            False,
            "medium",
            "archived projects",
            id="archived-project",
        ),
        pytest.param(
            EntityStatus.ACTIVE,
            EntityStatus.ARCHIVED,
            WorkerStatus.ACTIVE,
            False,
            False,
            "medium",
            "archived departments",
            id="archived-department",
        ),
        pytest.param(
            EntityStatus.ACTIVE,
            EntityStatus.ACTIVE,
            WorkerStatus.ACTIVE,
            True,
            False,
            "medium",
            "does not belong to project",
            id="department-project-mismatch",
        ),
        pytest.param(
            EntityStatus.ACTIVE,
            EntityStatus.ACTIVE,
            WorkerStatus.INACTIVE,
            False,
            False,
            "medium",
            "Inactive workers",
            id="inactive-worker",
        ),
        pytest.param(
            EntityStatus.ACTIVE,
            EntityStatus.ACTIVE,
            WorkerStatus.ACTIVE,
            False,
            True,
            "medium",
            "does not belong to department",
            id="worker-department-mismatch",
        ),
        pytest.param(
            EntityStatus.ACTIVE,
            EntityStatus.ACTIVE,
            WorkerStatus.ACTIVE,
            False,
            False,
            "critical",
            "Invalid priority",
            id="unknown-priority",
        ),
    ],
)
@pytest.mark.asyncio
async def test_work_item_service_rejects_invalid_creation_configuration(
    project_status,
    department_status,
    worker_status,
    wrong_project,
    wrong_department,
    priority,
    expected_error,
):
    service, repository, _, _, scope = make_work_item_service(
        project_status=project_status,
        department_status=department_status,
        worker_status=worker_status,
        department_project_id=uuid4() if wrong_project else None,
        worker_department_id=uuid4() if wrong_department else None,
    )

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.create_work_item(
            project_id=scope["project_id"],
            department_id=scope["department_id"],
            organization_id=scope["organization_id"],
            actor_user_id=uuid4(),
            title="Review onboarding queue",
            priority=priority,
            worker_id=scope["worker_id"],
        )

    assert expected_error in exception_info.value.message
    assert repository.create_data is None


@pytest.mark.asyncio
async def test_work_item_service_status_noop_has_no_history_or_audit():
    service, _, audit_repository, history_repository, scope = make_work_item_service()
    item = await service.create_work_item(
        project_id=scope["project_id"],
        department_id=scope["department_id"],
        organization_id=scope["organization_id"],
        actor_user_id=uuid4(),
        title="Review onboarding queue",
    )
    audit_count = len(audit_repository.events)

    result = await service.update_work_item_status(
        work_item_id=item.id,
        new_status="open",
        organization_id=scope["organization_id"],
        actor_user_id=uuid4(),
    )

    assert result.status == WorkStatus.OPEN
    assert history_repository.records == []
    assert len(audit_repository.events) == audit_count


@pytest.mark.asyncio
async def test_work_item_service_rejects_unknown_status_and_cross_tenant_worker_update():
    service, _, _, _, scope = make_work_item_service()
    item = await service.create_work_item(
        project_id=scope["project_id"],
        department_id=scope["department_id"],
        organization_id=scope["organization_id"],
        actor_user_id=uuid4(),
        title="Review onboarding queue",
    )

    with pytest.raises(UnprocessableEntityError) as status_error:
        await service.update_work_item_status(
            work_item_id=item.id,
            new_status="waiting",
            organization_id=scope["organization_id"],
            actor_user_id=uuid4(),
        )
    assert "Invalid status" in status_error.value.message
    with pytest.raises(UnprocessableEntityError) as assignment_error:
        await service.update_work_item(
            work_item_id=item.id,
            organization_id=scope["organization_id"],
            actor_user_id=uuid4(),
            update_data={"worker_id": uuid4()},
        )
    assert "not in this organization" in assignment_error.value.message


@pytest.mark.asyncio
async def test_work_item_service_validates_priority_before_listing():
    service, repository, _, _, scope = make_work_item_service()

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.list_work_items(
            project_id=scope["project_id"],
            organization_id=scope["organization_id"],
            limit=20,
            offset=0,
            priority="critical",
        )

    assert "Invalid priority" in exception_info.value.message
    assert repository.list_filters is None


__all__ = ["TestWorkItemEntity", "TestWorkItemStateTransition"]
