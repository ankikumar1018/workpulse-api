"""External queue adapters."""

from app.infrastructure.queues.cloud_tasks import CloudTasksQueue

__all__ = ["CloudTasksQueue"]
