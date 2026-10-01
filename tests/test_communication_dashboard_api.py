"""Smoke tests for the communication dashboard read API contract."""

from app.main import create_app
from app.schemas.responses.communication import (
    CommunicationJobHistoryResponse,
    CommunicationJobResponse,
    MessageResponse,
)


def test_communication_dashboard_routes_are_in_openapi_contract():
    openapi = create_app().openapi()

    assert "/api/v1/communication-jobs" in openapi["paths"]
    assert "/api/v1/communication-jobs/{job_id}/history" in openapi["paths"]
    assert "/api/v1/messages" in openapi["paths"]
    assert "/api/v1/messages/{message_id}/history" in openapi["paths"]


def test_communication_dashboard_responses_use_camel_case_fields():
    job_schema = CommunicationJobResponse.model_json_schema(by_alias=True)
    job_history_schema = CommunicationJobHistoryResponse.model_json_schema(by_alias=True)
    message_schema = MessageResponse.model_json_schema(by_alias=True)

    assert "attemptCount" in job_schema["properties"]
    assert "lastErrorMessage" in job_schema["properties"]
    assert "reasonCode" in job_history_schema["properties"]
    assert "deliveryStatus" in message_schema["properties"]
    assert "deliveredAt" in message_schema["properties"]
