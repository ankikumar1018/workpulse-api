"""External queue adapters."""

from app.infrastructure.queues.cloud_tasks import CloudTasksConfig, CloudTasksQueue

__all__ = ["CloudTasksConfig", "CloudTasksQueue"]
