"""Comprehensive tests for work item domain model and state transitions."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.enums import WorkStatus
from app.domain.work_item import InvalidTransitionError, WorkItem, WorkItemStateTransition
from app.infrastructure.db.models import WorkItem as WorkItemModel


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
        overdue=True,
    )

    assert repo.calls[0]["priority"] == "high"
    assert repo.calls[0]["overdue"] is True


__all__ = ["TestWorkItemEntity", "TestWorkItemStateTransition"]
