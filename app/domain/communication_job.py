"""Queue-independent communication job lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from app.domain.enums import CommunicationJobStatus


class InvalidCommunicationJobTransitionError(Exception):
    """Raised when a communication job changes to an invalid state."""


@dataclass
class CommunicationJob:
    """Logical work to perform, separate from queue and provider delivery state."""

    id: UUID
    organization_id: UUID
    job_key: str
    status: CommunicationJobStatus = CommunicationJobStatus.PENDING
    attempt_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    VALID_TRANSITIONS: ClassVar[dict[CommunicationJobStatus, set[CommunicationJobStatus]]] = {
        CommunicationJobStatus.PENDING: {
            CommunicationJobStatus.PROCESSING,
            CommunicationJobStatus.CANCELLED,
            CommunicationJobStatus.SUPPRESSED,
        },
        CommunicationJobStatus.PROCESSING: {
            CommunicationJobStatus.COMPLETED,
            CommunicationJobStatus.FAILED,
            CommunicationJobStatus.CANCELLED,
            CommunicationJobStatus.SUPPRESSED,
        },
        CommunicationJobStatus.COMPLETED: set(),
        CommunicationJobStatus.FAILED: {
            CommunicationJobStatus.PROCESSING,
            CommunicationJobStatus.CANCELLED,
            CommunicationJobStatus.SUPPRESSED,
        },
        CommunicationJobStatus.CANCELLED: set(),
        CommunicationJobStatus.SUPPRESSED: set(),
    }

    def transition_to(self, new_status: CommunicationJobStatus) -> None:
        """Move the job through its logical execution lifecycle."""
        if new_status == self.status:
            return
        if new_status not in self.VALID_TRANSITIONS.get(self.status, set()):
            allowed = ", ".join(
                status.value
                for status in sorted(
                    self.VALID_TRANSITIONS.get(self.status, set()),
                    key=lambda status: status.value,
                )
            )
            raise InvalidCommunicationJobTransitionError(
                f"Cannot transition communication job from '{self.status.value}' to "
                f"'{new_status.value}'. Allowed transitions: {allowed}"
            )
        self.status = new_status


__all__ = ["CommunicationJob", "InvalidCommunicationJobTransitionError"]
