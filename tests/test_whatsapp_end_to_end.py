"""Opt-in PostgreSQL dry run with real services and an offline Meta transport."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, time
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.dependencies import get_message_service
from app.api.errors import NotFoundError
from app.domain.enums import (
    Channel,
    CommunicationJobStatus,
    DeliveryStatus,
    ScheduleStatus,
    WorkStatus,
)
from app.infrastructure.db.models import (
    Department,
    Organization,
    Project,
    Schedule,
    Template,
    Worker,
    WorkItem,
)
from app.infrastructure.factory import Factory
from app.infrastructure.providers.whatsapp import WhatsAppCloudProvider
from app.main import create_app
from core.config import settings


@pytest.mark.asyncio
async def test_postgres_job_to_signed_webhook_and_delivery_history(request, monkeypatch):
    database_url = request.config.getoption("--whatsapp-test-db-url")
    if not database_url:
        pytest.skip("Pass --whatsapp-test-db-url for the disposable PostgreSQL dry run")
    parsed_url = make_url(database_url)
    if parsed_url.get_backend_name() != "postgresql" or not (parsed_url.database or "").startswith(
        "workpulse_test"
    ):
        pytest.fail("Dry runs require a disposable workpulse_test PostgreSQL database")

    async def reject_network(*_args, **_kwargs):
        pytest.fail("The dry run must never call the live Meta API")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject_network)
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "dry-run-app-secret")
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    organization = Organization(
                        id=uuid4(), name="Dry run", slug=f"dry-run-{uuid4()}"
                    )
                    session.add(organization)
                    await session.flush()
                    project = Project(id=uuid4(), organization_id=organization.id, name="Apollo")
                    session.add(project)
                    await session.flush()
                    department = Department(
                        id=uuid4(),
                        organization_id=organization.id,
                        project_id=project.id,
                        name="Install",
                    )
                    session.add(department)
                    await session.flush()
                    worker = Worker(
                        id=uuid4(),
                        organization_id=organization.id,
                        department_id=department.id,
                        full_name="Ada",
                        phone_number="+15551234567",
                    )
                    template = Template(
                        id=uuid4(),
                        organization_id=organization.id,
                        project_id=project.id,
                        name="Update",
                        body="Hi {{primary_contact_name}}, project {{project_name}} is {{work_status}}.",
                        variable_schema_json={
                            "project_name": "string",
                            "work_status": "string",
                            "primary_contact_name": "string",
                        },
                        provider_template_name="work_update",
                        provider_template_language="en_US",
                    )
                    session.add_all([worker, template])
                    await session.flush()
                    work_item = WorkItem(
                        id=uuid4(),
                        organization_id=organization.id,
                        project_id=project.id,
                        department_id=department.id,
                        worker_id=worker.id,
                        title="Review cabinetry",
                        status=WorkStatus.IN_PROGRESS,
                    )
                    session.add(work_item)
                    department.primary_contact_worker_id = worker.id
                    schedule = Schedule(
                        id=uuid4(),
                        organization_id=organization.id,
                        project_id=project.id,
                        department_id=department.id,
                        template_id=template.id,
                        timezone="UTC",
                        window_start_local=time(9),
                        window_end_local=time(17),
                        interval_seconds=3600,
                        status=ScheduleStatus.ACTIVE,
                    )
                    session.add(schedule)
                    await session.commit()
                    job_service = Factory.get_communication_job_service(session)
                    job = await job_service.create_job(
                        organization_id=organization.id,
                        schedule_id=schedule.id,
                        template_id=template.id,
                        work_item_id=work_item.id,
                        worker_id=worker.id,
                        channel=Channel.WHATSAPP,
                        execution_at=datetime(2026, 10, 7, 12, tzinfo=UTC),
                    )
                    requests = []

                    def accept_message(outbound_request):
                        requests.append(json.loads(outbound_request.content))
                        return httpx.Response(
                            200, json={"messages": [{"id": "wamid.postgres-dry-run"}]}
                        )

                    processor = Factory.get_message_job_processor(session)
                    async with httpx.AsyncClient(
                        transport=httpx.MockTransport(accept_message)
                    ) as provider_client:
                        provider = WhatsAppCloudProvider(
                            access_token="dry-run-token",
                            phone_number_id="dry-run-phone",
                            api_version="v24.0",
                            client=provider_client,
                        )
                        result = await processor.process(
                            job_id=job.id, organization_id=organization.id, provider=provider
                        )
                        duplicate = await processor.process(
                            job_id=job.id, organization_id=organization.id, provider=provider
                        )

                    assert (
                        result.job_status
                        == duplicate.job_status
                        == CommunicationJobStatus.COMPLETED
                    )
                    assert len(requests) == 1
                    assert requests[0]["type"] == "template"
                    assert requests[0]["template"]["components"][0]["parameters"] == [
                        {"type": "text", "text": "Ada"},
                        {"type": "text", "text": "Apollo"},
                        {"type": "text", "text": "in_progress"},
                    ]
                    message_service = Factory.get_message_service(session)
                    message = await message_service.get_message(
                        message_id=result.message_id, organization_id=organization.id
                    )
                    assert message.delivery_status == DeliveryStatus.SENT
                    assert message.rendered_body == "Hi Ada, project Apollo is in_progress."
                    app = create_app()
                    app.dependency_overrides[get_message_service] = lambda: message_service
                    try:
                        async with httpx.AsyncClient(
                            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
                        ) as webhook_client:
                            for delivery_status in ("delivered", "delivered", "sent"):
                                payload = json.dumps(
                                    {
                                        "entry": [
                                            {
                                                "changes": [
                                                    {
                                                        "value": {
                                                            "statuses": [
                                                                {
                                                                    "id": message.provider_message_id,
                                                                    "status": delivery_status,
                                                                }
                                                            ]
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ).encode()
                                signature = (
                                    "sha256="
                                    + hmac.new(
                                        b"dry-run-app-secret", payload, hashlib.sha256
                                    ).hexdigest()
                                )
                                response = await webhook_client.post(
                                    "/api/v1/webhooks/whatsapp",
                                    content=payload,
                                    headers={"X-Hub-Signature-256": signature},
                                )
                                assert response.status_code == 200
                    finally:
                        app.dependency_overrides.clear()
                    organization_id = organization.id
                    session.expire_all()
                    delivered = await message_service.get_message(
                        message_id=result.message_id, organization_id=organization_id
                    )
                    assert delivered.delivery_status == DeliveryStatus.DELIVERED
                    assert delivered.delivered_at is not None
                    history = await message_service.list_history(
                        message_id=delivered.id, organization_id=organization_id
                    )
                    assert [entry.new_status for entry in history] == [
                        DeliveryStatus.PROCESSING,
                        DeliveryStatus.SENT,
                        DeliveryStatus.DELIVERED,
                    ]
                    with pytest.raises(NotFoundError):
                        await message_service.list_history(
                            message_id=delivered.id, organization_id=uuid4()
                        )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
