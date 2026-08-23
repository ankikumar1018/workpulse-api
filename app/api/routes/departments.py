"""Department API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DepartmentCtrl
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.infrastructure.db.models import Department
from app.schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
    ListEnvelope,
    SuccessEnvelope,
)

router = APIRouter(prefix="/api/v1", tags=["Departments"])


def to_department_response(department: Department) -> DepartmentResponse:
    """Convert a department ORM object to its public response representation."""
    return DepartmentResponse(
        id=department.id,
        organization_id=department.organization_id,
        project_id=department.project_id,
        name=department.name,
        status=department.status.value,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )


@router.post(
    "/projects/{project_id}/departments",
    response_model=SuccessEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    project_id: UUID,
    request: DepartmentCreateRequest,
    controller: DepartmentCtrl,
    current_user: CurrentUser,
):
    """Create a department in the current user's project."""
    current_user.assert_admin()
    department = await controller.create_department(
        project_id=project_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        name=request.name,
    )
    return make_success_response(to_department_response(department))


@router.get("/projects/{project_id}/departments", response_model=ListEnvelope)
async def list_departments(
    project_id: UUID,
    controller: DepartmentCtrl,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    department_status: str | None = Query(None, alias="status"),
):
    """List departments in the current user's project."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    departments, total = await controller.list_departments(
        project_id=project_id,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        status=department_status,
    )
    return make_list_response(
        [to_department_response(department) for department in departments],
        total,
        limit,
        offset,
    )


@router.get("/departments/{department_id}", response_model=SuccessEnvelope)
async def get_department(
    department_id: UUID,
    controller: DepartmentCtrl,
    current_user: CurrentUser,
):
    """Get a department from the current user's organization."""
    current_user.assert_admin()
    department = await controller.get_department(
        department_id=department_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response(to_department_response(department))


@router.patch("/departments/{department_id}", response_model=SuccessEnvelope)
async def update_department(
    department_id: UUID,
    request: DepartmentUpdateRequest,
    controller: DepartmentCtrl,
    current_user: CurrentUser,
):
    """Update a department in the current user's organization."""
    current_user.assert_admin()
    department = await controller.update_department(
        department_id=department_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        update_data=request.model_dump(exclude_unset=True),
    )
    return make_success_response(to_department_response(department))


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_department(
    department_id: UUID,
    controller: DepartmentCtrl,
    current_user: CurrentUser,
):
    """Archive a department without deleting its historical records."""
    current_user.assert_admin()
    await controller.archive_department(
        department_id=department_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
    )


__all__ = ["router"]
