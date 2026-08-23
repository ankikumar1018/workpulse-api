"""Worker API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, WorkerCtrl
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.infrastructure.db.models import Worker
from app.schemas import (
    ListEnvelope,
    SuccessEnvelope,
    WorkerCreateRequest,
    WorkerResponse,
    WorkerUpdateRequest,
)

router = APIRouter(prefix="/api/v1", tags=["Workers"])


def to_worker_response(worker: Worker) -> WorkerResponse:
    """Convert a worker ORM object to its public response representation."""
    return WorkerResponse(
        id=worker.id,
        organization_id=worker.organization_id,
        department_id=worker.department_id,
        full_name=worker.full_name,
        phone_number=worker.phone_number,
        contact_channel=worker.contact_channel.value,
        consent_status=worker.consent_status.value,
        status=worker.status.value,
        created_at=worker.created_at,
        updated_at=worker.updated_at,
    )


@router.post(
    "/departments/{department_id}/workers",
    response_model=SuccessEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_worker(
    department_id: UUID,
    request: WorkerCreateRequest,
    controller: WorkerCtrl,
    current_user: CurrentUser,
):
    """Create a worker in the current user's department."""
    current_user.assert_admin()
    worker = await controller.create_worker(
        department_id=department_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        full_name=request.full_name,
        phone_number=request.phone_number,
        contact_channel=request.contact_channel,
        consent_status=request.consent_status,
    )
    return make_success_response(to_worker_response(worker))


@router.get("/departments/{department_id}/workers", response_model=ListEnvelope)
async def list_workers(
    department_id: UUID,
    controller: WorkerCtrl,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    worker_status: str | None = Query(None, alias="status"),
):
    """List workers in the current user's department."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    workers, total = await controller.list_workers(
        department_id=department_id,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        status=worker_status,
    )
    return make_list_response(
        [to_worker_response(worker) for worker in workers], total, limit, offset
    )


@router.get("/workers/{worker_id}", response_model=SuccessEnvelope)
async def get_worker(
    worker_id: UUID,
    controller: WorkerCtrl,
    current_user: CurrentUser,
):
    """Get a worker from the current user's organization."""
    current_user.assert_admin()
    worker = await controller.get_worker(
        worker_id=worker_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response(to_worker_response(worker))


@router.patch("/workers/{worker_id}", response_model=SuccessEnvelope)
async def update_worker(
    worker_id: UUID,
    request: WorkerUpdateRequest,
    controller: WorkerCtrl,
    current_user: CurrentUser,
):
    """Update a worker in the current user's organization."""
    current_user.assert_admin()
    worker = await controller.update_worker(
        worker_id=worker_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        update_data=request.model_dump(exclude_unset=True),
    )
    return make_success_response(to_worker_response(worker))


@router.delete("/workers/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_worker(
    worker_id: UUID,
    controller: WorkerCtrl,
    current_user: CurrentUser,
):
    """Deactivate a worker without deleting historical records."""
    current_user.assert_admin()
    await controller.archive_worker(
        worker_id=worker_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
    )


@router.post(
    "/departments/{department_id}/workers/{worker_id}/assignment",
    response_model=SuccessEnvelope,
)
async def assign_worker_to_department(
    department_id: UUID,
    worker_id: UUID,
    controller: WorkerCtrl,
    current_user: CurrentUser,
):
    """Assign an existing worker to an active department in the same organization."""
    current_user.assert_admin()
    worker = await controller.assign_worker_to_department(
        worker_id=worker_id,
        department_id=department_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
    )
    return make_success_response(to_worker_response(worker))


@router.delete(
    "/departments/{department_id}/workers/{worker_id}/assignment",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_worker_assignment(
    department_id: UUID,
    worker_id: UUID,
    controller: WorkerCtrl,
    current_user: CurrentUser,
):
    """Mark an assignment inactive so the worker is no longer a communication recipient."""
    current_user.assert_admin()
    await controller.remove_worker_assignment(
        worker_id=worker_id,
        department_id=department_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
    )


__all__ = ["router"]
