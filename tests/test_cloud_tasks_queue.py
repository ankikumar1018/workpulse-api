from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.job_queue import JobQueueError, QueueTaskRequest
from app.infrastructure.queues.cloud_tasks import CloudTasksConfig, CloudTasksQueue


class FakeCloudTasksClient:
    def __init__(self, *, response_name="accepted-task"):
        self.response_name = response_name
        self.created = []
        self.updated = []

    def create_task(self, *, parent, task):
        self.created.append((parent, task))
        return SimpleNamespace(name=self.response_name)

    def update_queue(self, *, queue):
        self.updated.append(queue)


def queue_config() -> CloudTasksConfig:
    return CloudTasksConfig(
        project_id="workpulse-prod",
        location="europe-west1",
        queue="communication-jobs",
        target_url="https://api.example.com/internal/tasks/communication",
        service_account_email="tasks@workpulse-prod.iam.gserviceaccount.com",
        audience="https://api.example.com",
        timeout_seconds=45,
        max_attempts=7,
        max_retry_seconds=900,
        max_retry_doublings=4,
        max_concurrent_dispatches=12,
    )


@pytest.mark.asyncio
async def test_cloud_tasks_enqueue_builds_stable_authenticated_request():
    client = FakeCloudTasksClient(response_name="tasks/accepted")
    built_tasks = []

    def task_factory(**kwargs):
        built_tasks.append(kwargs)
        return kwargs

    queue = CloudTasksQueue(queue_config(), client, task_factory=task_factory)
    request = QueueTaskRequest(
        job_id=uuid4(),
        organization_id=uuid4(),
        execution_at=datetime(2026, 10, 1, 12, 30, tzinfo=UTC),
    )

    result = await queue.enqueue(request)

    assert result.provider_name == "google_cloud_tasks"
    assert result.task_name == "tasks/accepted"
    assert client.created[0][0] == (
        "projects/workpulse-prod/locations/europe-west1/queues/communication-jobs"
    )
    assert built_tasks[0]["name"].endswith(f"communication-job-{request.job_id}")
    assert built_tasks[0]["job_id"] == str(request.job_id)
    assert built_tasks[0]["organization_id"] == str(request.organization_id)
    assert built_tasks[0]["target_url"] == "https://api.example.com/internal/tasks/communication"
    assert built_tasks[0]["service_account_email"].startswith("tasks@")
    assert built_tasks[0]["timeout_seconds"] == 45


@pytest.mark.asyncio
async def test_cloud_tasks_configures_retry_and_rate_controls():
    client = FakeCloudTasksClient()
    queue_values = []

    def queue_factory(**kwargs):
        queue_values.append(kwargs)
        return kwargs

    queue = CloudTasksQueue(queue_config(), client, queue_factory=queue_factory)

    await queue.configure_queue()

    assert client.updated == [queue_values[0]]
    assert queue_values[0]["max_attempts"] == 7
    assert queue_values[0]["max_retry_seconds"] == 900
    assert queue_values[0]["max_retry_doublings"] == 4
    assert queue_values[0]["max_concurrent_dispatches"] == 12


@pytest.mark.asyncio
async def test_cloud_tasks_failure_is_reported_without_mutating_logical_job():
    class RejectingClient(FakeCloudTasksClient):
        def create_task(self, *, parent, task):  # noqa: ARG002
            raise RuntimeError("queue unavailable")

    queue = CloudTasksQueue(queue_config(), RejectingClient(), task_factory=lambda **kwargs: kwargs)

    with pytest.raises(JobQueueError, match="rejected"):
        await queue.enqueue(
            QueueTaskRequest(
                job_id=uuid4(),
                organization_id=uuid4(),
                execution_at=datetime(2026, 10, 1, 12, 30, tzinfo=UTC),
            )
        )
