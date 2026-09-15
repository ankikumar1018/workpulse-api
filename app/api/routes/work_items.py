"""Work item API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, WorkItemCtrl
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.infrastructure.db.models import WorkItem
from app.schemas import ListEnvelope, SuccessEnvelope
from app.schemas.requests.work_item import WorkItemCreateRequest, WorkItemUpdateStatusRequest
from app.schemas.responses.work_item import WorkItemResponse, WorkItemTransitionResponse

router = APIRouter(prefix="/api/v1", tags=["Work Items"])


def to_work_item_response(work_item: WorkItem) -> WorkItemResponse:
    """Convert a work item ORM object to its public response representation."""
    return WorkItemResponse(
        id=work_item.id,
        organization_id=work_item.organization_id,
        project_id=work_item.project_id,
        department_id=work_item.department_id,
        worker_id=work_item.worker_id,
        title=work_item.title,
        description=work_item.description,
        priority=work_item.priority.value,
        status=work_item.status.value,
        due_at=work_item.due_at,
        created_at=work_item.created_at,
        updated_at=work_item.updated_at,
    )


@router.post(
    "/projects/{project_id}/work_items",
    response_model=SuccessEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_item(
    project_id: UUID,
    request: WorkItemCreateRequest,
    controller: WorkItemCtrl,
    current_user: CurrentUser,
):
    """Create a work item in a project."""
    current_user.assert_admin()
    work_item = await controller.create_work_item(
        project_id=project_id,
        department_id=request.department_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        title=request.title,
        description=request.description,
        priority=request.priority,
        worker_id=request.worker_id,
        due_at=request.due_at,
    )
    return make_success_response(to_work_item_response(work_item))


@router.get("/projects/{project_id}/work_items", response_model=ListEnvelope)
async def list_work_items(
    project_id: UUID,
    controller: WorkItemCtrl,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    department_id: UUID | None = None,
    status: str | None = None,
):
    """List work items in a project."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    work_items, total = await controller.list_work_items(
        project_id=project_id,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        department_id=department_id,
        status=status,
    )
    return make_list_response(
        [to_work_item_response(wi) for wi in work_items], total, limit, offset
    )


@router.get("/work_items/{work_item_id}", response_model=SuccessEnvelope)
async def get_work_item(
    work_item_id: UUID,
    controller: WorkItemCtrl,
    current_user: CurrentUser,
):
    """Get a work item from the current user's organization."""
    current_user.assert_admin()
    work_item = await controller.get_work_item(
        work_item_id=work_item_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response(to_work_item_response(work_item))


@router.patch(
    "/work_items/{work_item_id}/status",
    response_model=SuccessEnvelope,
    status_code=status.HTTP_200_OK,
)
async def update_work_item_status(
    work_item_id: UUID,
    request: WorkItemUpdateStatusRequest,
    controller: WorkItemCtrl,
    current_user: CurrentUser,
):
    """Update a work item's status with transition validation.

    This endpoint enforces the work item state machine, ensuring only valid
    transitions are allowed. Invalid transitions will return an error with
    information about allowed transitions from the current state.
    """
    current_user.assert_admin()
    old_work_item = await controller.get_work_item(
        work_item_id=work_item_id,
        organization_id=current_user.organization_id,
    )
    old_status = old_work_item.status.value

    work_item = await controller.update_work_item_status(
        work_item_id=work_item_id,
        new_status=request.status,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
    )

    # Return detailed transition response
    response = WorkItemTransitionResponse(
        work_item_id=work_item.id,
        old_status=old_status,
        new_status=work_item.status.value,
        timestamp=work_item.updated_at,
    )
    return make_success_response(response)


__all__ = ["router"]
