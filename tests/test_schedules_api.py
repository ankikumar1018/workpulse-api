"""Smoke tests for schedule API registration and request aliases."""

from app.main import create_app
from app.schemas import ScheduleCreateRequest, ScheduleUpdateRequest


def test_schedule_routes_are_in_openapi_contract():
    openapi = create_app().openapi()

    assert "/api/v1/projects/{project_id}/schedules" in openapi["paths"]
    assert "/api/v1/schedules/{schedule_id}/activate" in openapi["paths"]
    assert "/api/v1/schedules/{schedule_id}/pause" in openapi["paths"]


def test_schedule_requests_accept_camel_case_contract_fields():
    create_schema = ScheduleCreateRequest.model_json_schema(by_alias=True)
    update_schema = ScheduleUpdateRequest.model_json_schema(by_alias=True)

    assert "departmentId" in create_schema["properties"]
    assert "windowStartLocal" in create_schema["properties"]
    assert "intervalSeconds" in update_schema["properties"]
