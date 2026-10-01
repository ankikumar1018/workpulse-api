"""Provider-neutral queue contracts for logical communication jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


class JobQueueError(Exception):
    """Raised when a queue cannot accept a logical job."""


@dataclass(frozen=True)
class QueueTaskRequest:
    """Authenticated HTTP task data derived from a logical job."""

    job_id: UUID
    organization_id: UUID
    execution_at: datetime


@dataclass(frozen=True)
class QueueTaskResult:
    """Provider-independent result of queue acceptance."""

    provider_name: str
    task_name: str


class JobQueue(Protocol):
    """Enqueue logical communication jobs for asynchronous processing."""

    async def enqueue(self, request: QueueTaskRequest) -> QueueTaskResult:
        """Submit a job and return the provider's task identity."""


__all__ = ["JobQueue", "JobQueueError", "QueueTaskRequest", "QueueTaskResult"]
