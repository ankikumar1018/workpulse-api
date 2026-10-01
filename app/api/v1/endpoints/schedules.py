"""Project-scoped schedule configuration endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, ScheduleSvc
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.domain.enums import ScheduleStatus
from app.infrastructure.db.models import Schedule
from app.schemas import (
    ListEnvelope,
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
    SuccessEnvelope,
)

router = APIRouter(tags=["Schedules"])


def to_schedule_response(schedule: Schedule) -> ScheduleResponse:
    """Convert a schedule ORM object to its public response representation."""
    return ScheduleResponse(
        id=schedule.id,
        organization_id=schedule.organization_id,
        project_id=schedule.project_id,
        department_id=schedule.department_id,
        template_id=schedule.template_id,
        timezone=schedule.timezone,
        window_start_local=schedule.window_start_local,
        window_end_local=schedule.window_end_local,
        interval_seconds=schedule.interval_seconds,
        status=schedule.status.value,
        next_run_at_utc=schedule.next_run_at_utc,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


@router.post(
    "/projects/{project_id}/schedules",
    response_model=SuccessEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    project_id: UUID,
    request: ScheduleCreateRequest,
    controller: ScheduleSvc,
    current_user: CurrentUser,
):
    """Create a paused schedule for the current organization."""
    current_user.assert_admin()
    schedule = await controller.create_schedule(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        project_id=project_id,
        department_id=request.department_id,
        template_id=request.template_id,
        timezone=request.timezone,
        window_start_local=request.window_start_local,
        window_end_local=request.window_end_local,
        interval_seconds=request.interval_seconds,
    )
    return make_success_response(to_schedule_response(schedule))


@router.get("/projects/{project_id}/schedules", response_model=ListEnvelope)
async def list_schedules(
    project_id: UUID,
    controller: ScheduleSvc,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    schedule_status: Annotated[ScheduleStatus | None, Query(alias="status")] = None,
):
    """List schedules for a project in the current organization."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    schedules, total = await controller.list_schedules(
        project_id=project_id,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        status=schedule_status.value if schedule_status else None,
    )
    return make_list_response(
        [to_schedule_response(schedule) for schedule in schedules], total, limit, offset
    )


@router.get("/schedules/{schedule_id}", response_model=SuccessEnvelope)
async def get_schedule(
    schedule_id: UUID,
    controller: ScheduleSvc,
    current_user: CurrentUser,
):
    """Get one schedule from the current organization."""
    current_user.assert_admin()
    schedule = await controller.get_schedule(
        schedule_id=schedule_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response(to_schedule_response(schedule))


@router.patch("/schedules/{schedule_id}", response_model=SuccessEnvelope)
async def update_schedule(
    schedule_id: UUID,
    request: ScheduleUpdateRequest,
    controller: ScheduleSvc,
    current_user: CurrentUser,
):
    """Update a paused schedule in the current organization."""
    current_user.assert_admin()
    schedule = await controller.update_schedule(
        schedule_id=schedule_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        update_data=request.model_dump(exclude_unset=True),
    )
    return make_success_response(to_schedule_response(schedule))


@router.post("/schedules/{schedule_id}/activate", response_model=SuccessEnvelope)
async def activate_schedule(
    schedule_id: UUID,
    controller: ScheduleSvc,
    current_user: CurrentUser,
):
    """Activate a schedule after revalidating its current project scope."""
    current_user.assert_admin()
    schedule = await controller.set_schedule_status(
        schedule_id=schedule_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        status=ScheduleStatus.ACTIVE,
    )
    return make_success_response(to_schedule_response(schedule))


@router.post("/schedules/{schedule_id}/pause", response_model=SuccessEnvelope)
async def pause_schedule(
    schedule_id: UUID,
    controller: ScheduleSvc,
    current_user: CurrentUser,
):
    """Pause a schedule in the current organization."""
    current_user.assert_admin()
    schedule = await controller.set_schedule_status(
        schedule_id=schedule_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        status=ScheduleStatus.PAUSED,
    )
    return make_success_response(to_schedule_response(schedule))


__all__ = ["router", "to_schedule_response"]
