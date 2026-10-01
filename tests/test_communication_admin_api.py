"""Integration tests for tenant-scoped communication administration APIs."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    AuthContext,
    get_auth_context,
    get_communication_job_service,
    get_message_service,
    get_project_service,
)
from app.api.errors import NotFoundError
from app.domain.enums import Channel, CommunicationJobStatus, DeliveryStatus, EntityStatus
from app.main import app, create_app

ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000002")
MESSAGE_ID = UUID("10000000-0000-0000-0000-000000000001")
JOB_ID = UUID("20000000-0000-0000-0000-000000000001")
PROJECT_ID = UUID("70000000-0000-0000-0000-000000000001")
TIMESTAMP = datetime(2026, 1, 1, 12, tzinfo=UTC)


class FakeMessageService:
    """Capture message service calls without requiring persistence."""

    def __init__(self):
        self.list_calls: list[dict] = []
        self.history_calls: list[dict] = []

    async def list_messages(self, **kwargs):
        self.list_calls.append(kwargs)
        return [make_message()], 3

    async def list_history(self, **kwargs):
        self.history_calls.append(kwargs)
        return [make_message_history()]


class FakeCommunicationJobService:
    """Capture communication job service calls without requiring persistence."""

    def __init__(self):
        self.list_calls: list[dict] = []
        self.history_calls: list[dict] = []

    async def list_jobs(self, **kwargs):
        self.list_calls.append(kwargs)
        return [make_job()], 2

    async def list_history(self, **kwargs):
        self.history_calls.append(kwargs)
        return [make_job_history()]


class FakeProjectService:
    """Capture project mutation and list calls without requiring persistence."""

    def __init__(self):
        self.create_calls: list[dict] = []
        self.list_calls: list[dict] = []

    async def create_project(self, **kwargs):
        self.create_calls.append(kwargs)
        return make_project(name=kwargs["name"])

    async def list_projects(self, **kwargs):
        self.list_calls.append(kwargs)
        return [make_project(name="Northstar")], 1


def make_message():
    return SimpleNamespace(
        id=MESSAGE_ID,
        organization_id=ORGANIZATION_ID,
        schedule_id=None,
        work_item_id=None,
        worker_id=UUID("30000000-0000-0000-0000-000000000001"),
        channel=Channel.WHATSAPP,
        recipient_phone_number="+15551234567",
        rendered_body="Reminder",
        provider_name="neutral-provider",
        provider_message_id="provider-message-1",
        delivery_status=DeliveryStatus.SENT,
        error_code=None,
        error_message=None,
        sent_at=TIMESTAMP,
        delivered_at=None,
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )


def make_message_history():
    return SimpleNamespace(
        id=UUID("40000000-0000-0000-0000-000000000001"),
        organization_id=ORGANIZATION_ID,
        message_id=MESSAGE_ID,
        previous_status=DeliveryStatus.QUEUED,
        new_status=DeliveryStatus.SENT,
        actor_user_id=None,
        provider_name="neutral-provider",
        provider_message_id="provider-message-1",
        error_code=None,
        error_message=None,
        created_at=TIMESTAMP,
    )


def make_job():
    return SimpleNamespace(
        id=JOB_ID,
        organization_id=ORGANIZATION_ID,
        schedule_id=None,
        template_id=UUID("50000000-0000-0000-0000-000000000001"),
        work_item_id=None,
        worker_id=UUID("30000000-0000-0000-0000-000000000001"),
        channel=Channel.WHATSAPP,
        execution_at=TIMESTAMP,
        status=CommunicationJobStatus.COMPLETED,
        attempt_count=1,
        last_error_code=None,
        last_error_message=None,
        started_at=TIMESTAMP,
        completed_at=TIMESTAMP,
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )


def make_job_history():
    return SimpleNamespace(
        id=UUID("60000000-0000-0000-0000-000000000001"),
        organization_id=ORGANIZATION_ID,
        job_id=JOB_ID,
        previous_status=CommunicationJobStatus.PROCESSING,
        new_status=CommunicationJobStatus.COMPLETED,
        reason_code=None,
        reason=None,
        queue_reference="queue-1",
        created_at=TIMESTAMP,
    )


def make_project(*, name: str):
    return SimpleNamespace(
        id=UUID("80000000-0000-0000-0000-000000000001"),
        organization_id=ORGANIZATION_ID,
        name=name,
        description="Operations project",
        status=EntityStatus.ACTIVE,
        start_date=None,
        end_date=None,
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )


@pytest.fixture
def admin_client():
    message_service = FakeMessageService()
    job_service = FakeCommunicationJobService()
    user = AuthContext(
        user_id=UUID("70000000-0000-0000-0000-000000000001"),
        organization_id=ORGANIZATION_ID,
    )

    app.dependency_overrides[get_auth_context] = lambda: user
    app.dependency_overrides[get_message_service] = lambda: message_service
    app.dependency_overrides[get_communication_job_service] = lambda: job_service
    try:
        yield TestClient(app), message_service, job_service
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def project_client():
    project_service = FakeProjectService()
    user = AuthContext(
        user_id=UUID("70000000-0000-0000-0000-000000000001"),
        organization_id=ORGANIZATION_ID,
    )

    app.dependency_overrides[get_auth_context] = lambda: user
    app.dependency_overrides[get_project_service] = lambda: project_service
    try:
        yield TestClient(app), project_service
    finally:
        app.dependency_overrides.clear()


def test_message_list_forwards_tenant_filter_and_pagination(admin_client):
    client, message_service, _ = admin_client

    response = client.get(f"/api/v1/messages?status=sent&project_id={PROJECT_ID}&limit=1&offset=2")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"][0]["deliveryStatus"] == "sent"
    assert body["pagination"] == {"total": 3, "limit": 1, "offset": 2, "hasMore": False}
    assert message_service.list_calls == [
        {
            "organization_id": ORGANIZATION_ID,
            "status": DeliveryStatus.SENT,
            "project_id": PROJECT_ID,
            "limit": 1,
            "offset": 2,
        }
    ]


def test_job_list_uses_default_pagination_and_tenant(admin_client):
    client, _, job_service = admin_client

    response = client.get("/api/v1/communication-jobs?status=completed")

    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "total": 2,
        "limit": 20,
        "offset": 0,
        "hasMore": False,
    }
    assert job_service.list_calls == [
        {
            "organization_id": ORGANIZATION_ID,
            "status": CommunicationJobStatus.COMPLETED,
            "project_id": None,
            "limit": 20,
            "offset": 0,
        }
    ]


def test_history_endpoints_return_success_envelopes_and_tenant_scope(admin_client):
    client, message_service, job_service = admin_client

    message_response = client.get(f"/api/v1/messages/{MESSAGE_ID}/history")
    job_response = client.get(f"/api/v1/communication-jobs/{JOB_ID}/history")

    assert message_response.status_code == 200
    assert message_response.json()["data"][0]["newStatus"] == "sent"
    assert job_response.status_code == 200
    assert job_response.json()["data"][0]["newStatus"] == "completed"
    assert message_service.history_calls == [
        {"message_id": MESSAGE_ID, "organization_id": ORGANIZATION_ID}
    ]
    assert job_service.history_calls == [{"job_id": JOB_ID, "organization_id": ORGANIZATION_ID}]


def test_non_admin_is_forbidden(admin_client):
    client, _, _ = admin_client
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id=UUID("70000000-0000-0000-0000-000000000001"),
        organization_id=ORGANIZATION_ID,
        role="worker",
    )

    response = client.get("/api/v1/messages")

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "FORBIDDEN",
        "message": "Admin role required",
        "details": None,
    }


def test_invalid_pagination_returns_validation_envelope(admin_client):
    client, _, _ = admin_client

    response = client.get("/api/v1/messages?limit=0")

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["details"][0]["field"] == "query.limit"


def test_missing_bearer_token_is_unauthorized():
    client = TestClient(create_app())

    response = client.get("/api/v1/messages")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_history_not_found_preserves_error_envelope(admin_client):
    client, _, _ = admin_client

    async def missing_history(**_kwargs):
        raise NotFoundError("Message not found")

    app.dependency_overrides[get_message_service] = lambda: SimpleNamespace(
        list_history=missing_history
    )

    response = client.get(f"/api/v1/messages/{MESSAGE_ID}/history")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "NOT_FOUND",
        "message": "Message not found",
        "details": None,
    }


def test_other_organization_is_not_used_for_auth_context(admin_client):
    client, message_service, _ = admin_client
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id=UUID("70000000-0000-0000-0000-000000000001"),
        organization_id=OTHER_ORGANIZATION_ID,
    )

    response = client.get("/api/v1/messages")

    assert response.status_code == 200
    assert message_service.list_calls[0]["organization_id"] == OTHER_ORGANIZATION_ID


def test_project_create_forwards_actor_and_tenant_and_returns_envelope(project_client):
    client, project_service = project_client

    response = client.post(
        "/api/v1/projects",
        json={"name": "Northstar", "description": "Operations project"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Northstar"
    assert project_service.create_calls == [
        {
            "organization_id": ORGANIZATION_ID,
            "actor_user_id": UUID("70000000-0000-0000-0000-000000000001"),
            "name": "Northstar",
            "description": "Operations project",
            "start_date": None,
            "end_date": None,
        }
    ]


def test_project_list_forwards_filter_and_pagination(project_client):
    client, project_service = project_client

    response = client.get("/api/v1/projects?status=active&limit=5&offset=10")

    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "total": 1,
        "limit": 5,
        "offset": 10,
        "hasMore": False,
    }
    assert project_service.list_calls == [
        {
            "organization_id": ORGANIZATION_ID,
            "limit": 5,
            "offset": 10,
            "status": "active",
        }
    ]


def test_project_create_validation_uses_error_contract(project_client):
    client, project_service = project_client

    response = client.post("/api/v1/projects", json={"name": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["field"] == "body.name"
    assert project_service.create_calls == []
