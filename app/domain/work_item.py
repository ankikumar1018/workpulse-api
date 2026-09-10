"""Work item domain model and state transition rules."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from app.domain.enums import WorkStatus


class InvalidTransitionError(Exception):
    """Raised when a work item state transition is invalid."""

    pass


class WorkItemStateTransition:
    """Defines valid state transitions for work items.

    Transition rules:
    - OPEN can go to: IN_PROGRESS, BLOCKED, CANCELLED
    - IN_PROGRESS can go to: BLOCKED, DONE, CANCELLED
    - BLOCKED can go to: IN_PROGRESS, OPEN, CANCELLED
    - DONE is terminal (no outgoing transitions)
    - CANCELLED is terminal (no outgoing transitions)
    """

    # Define valid transitions as a dict mapping current state to allowed next states
    VALID_TRANSITIONS: ClassVar[dict[WorkStatus, set[WorkStatus]]] = {
        WorkStatus.OPEN: {WorkStatus.IN_PROGRESS, WorkStatus.BLOCKED, WorkStatus.CANCELLED},
        WorkStatus.IN_PROGRESS: {WorkStatus.BLOCKED, WorkStatus.DONE, WorkStatus.CANCELLED},
        WorkStatus.BLOCKED: {WorkStatus.IN_PROGRESS, WorkStatus.OPEN, WorkStatus.CANCELLED},
        WorkStatus.DONE: set(),  # Terminal state
        WorkStatus.CANCELLED: set(),  # Terminal state
    }

    @classmethod
    def is_valid_transition(cls, from_status: WorkStatus, to_status: WorkStatus) -> bool:
        """Check if a transition from one status to another is allowed.

        Args:
            from_status: Current work item status
            to_status: Target work item status

        Returns:
            True if the transition is allowed, False otherwise
        """
        return to_status in cls.VALID_TRANSITIONS.get(from_status, set())

    @classmethod
    def validate_transition(cls, from_status: WorkStatus, to_status: WorkStatus) -> None:
        """Validate a transition and raise an error if it's invalid.

        Args:
            from_status: Current work item status
            to_status: Target work item status

        Raises:
            InvalidTransitionError: If the transition is not allowed
        """
        if from_status == to_status:
            # No-op transitions are valid (idempotent)
            return

        if not cls.is_valid_transition(from_status, to_status):
            allowed = cls.VALID_TRANSITIONS.get(from_status, set())
            allowed_str = ", ".join(s.value for s in sorted(allowed, key=lambda x: x.value))
            raise InvalidTransitionError(
                f"Cannot transition work item from '{from_status.value}' to "
                f"'{to_status.value}'. Allowed transitions: {allowed_str}"
            )

    @classmethod
    def get_allowed_transitions(cls, current_status: WorkStatus) -> set[WorkStatus]:
        """Get all allowed next states from the current state.

        Args:
            current_status: Current work item status

        Returns:
            Set of allowed next states
        """
        return cls.VALID_TRANSITIONS.get(current_status, set()).copy()


class WorkItem:
    """Domain entity for a work item with lifecycle management.

    This is a domain model that enforces business rules for work item state changes.
    It can be used both for validation logic and as a value object.
    """

    def __init__(
        self,
        id: UUID,
        organization_id: UUID,
        project_id: UUID,
        department_id: UUID,
        status: WorkStatus,
    ):
        self.id = id
        self.organization_id = organization_id
        self.project_id = project_id
        self.department_id = department_id
        self._status = status

    @property
    def status(self) -> WorkStatus:
        """Get the current work item status."""
        return self._status

    def can_transition_to(self, new_status: WorkStatus) -> bool:
        """Check if this work item can transition to the given status.

        Args:
            new_status: The target status

        Returns:
            True if the transition is allowed, False otherwise
        """
        return WorkItemStateTransition.is_valid_transition(self._status, new_status)

    def transition_to(self, new_status: WorkStatus) -> None:
        """Transition this work item to a new status.

        Args:
            new_status: The target status

        Raises:
            InvalidTransitionError: If the transition is not allowed
        """
        WorkItemStateTransition.validate_transition(self._status, new_status)
        self._status = new_status

    def get_allowed_transitions(self) -> set[WorkStatus]:
        """Get all allowed next states from the current state.

        Returns:
            Set of allowed next states
        """
        return WorkItemStateTransition.get_allowed_transitions(self._status)

    def is_terminal(self) -> bool:
        """Check if the current status is terminal (no further transitions allowed).

        Returns:
            True if no transitions are allowed, False otherwise
        """
        return len(self.get_allowed_transitions()) == 0


__all__ = ["InvalidTransitionError", "WorkItem", "WorkItemStateTransition"]
