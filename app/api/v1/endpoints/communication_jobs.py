"""Admin read APIs for logical communication jobs and their history."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CommunicationJobSvc, CurrentUser
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.domain.enums import CommunicationJobStatus
from app.infrastructure.db.models import CommunicationJob, CommunicationJobStatusHistory
from app.schemas import ListEnvelope, SuccessEnvelope
from app.schemas.responses.communication import (
    CommunicationJobHistoryResponse,
    CommunicationJobResponse,
)

router = APIRouter(prefix="/communication-jobs", tags=["Communication Jobs"])


def to_job_response(job: CommunicationJob) -> CommunicationJobResponse:
    """Convert a logical job to its public operational representation."""
    return CommunicationJobResponse(
        id=job.id,
        organization_id=job.organization_id,
        schedule_id=job.schedule_id,
        template_id=job.template_id,
        work_item_id=job.work_item_id,
        worker_id=job.worker_id,
        channel=job.channel.value,
        execution_at=job.execution_at,
        status=job.status.value,
        attempt_count=job.attempt_count,
        last_error_code=job.last_error_code,
        last_error_message=job.last_error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def to_job_history_response(
    history: CommunicationJobStatusHistory,
) -> CommunicationJobHistoryResponse:
    """Convert one persisted job transition to its public representation."""
    return CommunicationJobHistoryResponse(
        id=history.id,
        organization_id=history.organization_id,
        job_id=history.job_id,
        previous_status=history.previous_status.value if history.previous_status else None,
        new_status=history.new_status.value,
        reason_code=history.reason_code,
        reason=history.reason,
        queue_reference=history.queue_reference,
        created_at=history.created_at,
    )


@router.get("", response_model=ListEnvelope)
async def list_communication_jobs(
    controller: CommunicationJobSvc,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    status: Annotated[CommunicationJobStatus | None, Query()] = None,
):
    """List logical communication jobs for the current organization."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    jobs, total = await controller.list_jobs(
        organization_id=current_user.organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return make_list_response([to_job_response(job) for job in jobs], total, limit, offset)


@router.get("/{job_id}/history", response_model=SuccessEnvelope)
async def list_communication_job_history(
    job_id: UUID,
    controller: CommunicationJobSvc,
    current_user: CurrentUser,
):
    """List tenant-scoped state transitions for one communication job."""
    current_user.assert_admin()
    history = await controller.list_history(
        job_id=job_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response([to_job_history_response(entry) for entry in history])
