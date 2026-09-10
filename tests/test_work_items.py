"""Comprehensive tests for work item domain model and state transitions."""

import pytest

from app.domain.enums import WorkStatus
from app.domain.work_item import InvalidTransitionError, WorkItem, WorkItemStateTransition


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


__all__ = ["TestWorkItemEntity", "TestWorkItemStateTransition"]
