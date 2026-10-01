"""Google Cloud Tasks adapter for communication-job HTTP dispatch."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from app.domain.job_queue import JobQueueError, QueueTaskRequest, QueueTaskResult
from core.config import Settings


class CloudTasksQueue:
    """Create authenticated, idempotently named Cloud Tasks HTTP requests."""

    provider_name = "google_cloud_tasks"

    def __init__(
        self,
        settings: Settings,
        client: Any | None = None,
        task_factory: Any | None = None,
        queue_factory: Any | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._task_factory = task_factory
        self._queue_factory = queue_factory

    async def enqueue(self, request: QueueTaskRequest) -> QueueTaskResult:
        """Enqueue one logical job without changing its database state."""
        if not self._settings.GCP_PROJECT_ID or not self._settings.CLOUD_TASKS_TARGET_URL:
            raise JobQueueError("GCP project ID and Cloud Tasks target URL must be configured.")

        client = self._client or self._build_client()
        task_name = self._task_name(request.job_id)
        task = self._build_task(request, task_name)
        try:
            response = client.create_task(
                parent=self._queue_path(),
                task=task,
            )
        except Exception as error:
            raise JobQueueError("Cloud Tasks rejected the communication job.") from error

        accepted_name = getattr(response, "name", None) or task_name
        return QueueTaskResult(provider_name=self.provider_name, task_name=accepted_name)

    async def configure_queue(self) -> None:
        """Apply retry and rate controls to the configured Cloud Tasks queue."""
        client = self._client or self._build_client()
        queue = self._build_queue()
        try:
            client.update_queue(queue=queue)
        except Exception as error:
            raise JobQueueError("Cloud Tasks queue configuration was rejected.") from error

    def _build_client(self) -> Any:
        try:
            from google.cloud import tasks_v2
        except ImportError as error:
            raise JobQueueError(
                "google-cloud-tasks must be installed to use Cloud Tasks."
            ) from error
        return tasks_v2.CloudTasksClient()

    def _build_task(self, request: QueueTaskRequest, task_name: str) -> Any:
        if self._task_factory is not None:
            return self._task_factory(
                name=task_name,
                job_id=str(request.job_id),
                organization_id=str(request.organization_id),
                execution_at=request.execution_at,
                target_url=self._settings.CLOUD_TASKS_TARGET_URL,
                service_account_email=self._settings.CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL,
                audience=self._settings.CLOUD_TASKS_AUDIENCE,
                timeout_seconds=self._settings.CLOUD_TASKS_TIMEOUT_SECONDS,
            )
        try:
            from google.cloud import tasks_v2
        except ImportError as error:
            raise JobQueueError(
                "google-cloud-tasks must be installed to use Cloud Tasks."
            ) from error

        body = json.dumps(
            {
                "job_id": str(request.job_id),
                "organization_id": str(request.organization_id),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        oidc_token: dict[str, str] = {}
        if self._settings.CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL:
            oidc_token["service_account_email"] = self._settings.CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL
        if self._settings.CLOUD_TASKS_AUDIENCE:
            oidc_token["audience"] = self._settings.CLOUD_TASKS_AUDIENCE

        http_request = tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=self._settings.CLOUD_TASKS_TARGET_URL,
            headers={"Content-Type": "application/json"},
            body=body,
            oidc_token=oidc_token or None,
        )
        return tasks_v2.Task(
            name=task_name,
            http_request=http_request,
            schedule_time=request.execution_at,
            dispatch_deadline=timedelta(seconds=self._settings.CLOUD_TASKS_TIMEOUT_SECONDS),
        )

    def _build_queue(self) -> Any:
        if self._queue_factory is not None:
            return self._queue_factory(
                name=self._queue_path(),
                max_attempts=self._settings.CLOUD_TASKS_MAX_ATTEMPTS,
                max_retry_seconds=self._settings.CLOUD_TASKS_MAX_RETRY_SECONDS,
                max_retry_doublings=self._settings.CLOUD_TASKS_MAX_RETRY_DOUBLINGS,
                max_concurrent_dispatches=self._settings.CLOUD_TASKS_MAX_CONCURRENT_DISPATCHES,
            )
        try:
            from google.cloud import tasks_v2
        except ImportError as error:
            raise JobQueueError(
                "google-cloud-tasks must be installed to use Cloud Tasks."
            ) from error

        retry_config = tasks_v2.RetryConfig(
            max_attempts=self._settings.CLOUD_TASKS_MAX_ATTEMPTS,
            max_retry_duration=timedelta(seconds=self._settings.CLOUD_TASKS_MAX_RETRY_SECONDS),
            max_doublings=self._settings.CLOUD_TASKS_MAX_RETRY_DOUBLINGS,
        )
        rate_limits = None
        if self._settings.CLOUD_TASKS_MAX_CONCURRENT_DISPATCHES is not None:
            rate_limits = tasks_v2.RateLimits(
                max_concurrent_dispatches=self._settings.CLOUD_TASKS_MAX_CONCURRENT_DISPATCHES
            )
        return tasks_v2.Queue(
            name=self._queue_path(),
            retry_config=retry_config,
            rate_limits=rate_limits,
        )

    def _queue_path(self) -> str:
        if not self._settings.GCP_PROJECT_ID:
            raise JobQueueError("GCP project ID must be configured.")
        return (
            f"projects/{self._settings.GCP_PROJECT_ID}/locations/"
            f"{self._settings.CLOUD_TASKS_LOCATION}/queues/{self._settings.CLOUD_TASKS_QUEUE}"
        )

    def _task_name(self, job_id: Any) -> str:
        if not self._settings.GCP_PROJECT_ID:
            raise JobQueueError("GCP project ID must be configured.")
        return (
            f"projects/{self._settings.GCP_PROJECT_ID}/locations/"
            f"{self._settings.CLOUD_TASKS_LOCATION}/queues/{self._settings.CLOUD_TASKS_QUEUE}/"
            f"tasks/communication-job-{job_id}"
        )


__all__ = ["CloudTasksQueue"]
