"""Project API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ProjectCtrl
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.infrastructure.db.models import Project
from app.schemas import (
    ListEnvelope,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    SuccessEnvelope,
)

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


def to_project_response(project: Project) -> ProjectResponse:
    """Convert a project ORM object to its public response representation."""
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        start_date=project.start_date,
        end_date=project.end_date,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post("", response_model=SuccessEnvelope, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    controller: ProjectCtrl,
    current_user: CurrentUser,
):
    """Create a project in the current user's organization."""
    current_user.assert_admin()
    project = await controller.create_project(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        name=request.name,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    return make_success_response(to_project_response(project))


@router.get("", response_model=ListEnvelope)
async def list_projects(
    controller: ProjectCtrl,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    project_status: str | None = Query(None, alias="status"),
):
    """List projects in the current user's organization."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    projects, total = await controller.list_projects(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        status=project_status,
    )
    return make_list_response(
        [to_project_response(project) for project in projects], total, limit, offset
    )


@router.get("/{project_id}", response_model=SuccessEnvelope)
async def get_project(
    project_id: UUID,
    controller: ProjectCtrl,
    current_user: CurrentUser,
):
    """Get a project from the current user's organization."""
    current_user.assert_admin()
    project = await controller.get_project(
        project_id=project_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response(to_project_response(project))


@router.patch("/{project_id}", response_model=SuccessEnvelope)
async def update_project(
    project_id: UUID,
    request: ProjectUpdateRequest,
    controller: ProjectCtrl,
    current_user: CurrentUser,
):
    """Update a project in the current user's organization."""
    current_user.assert_admin()
    project = await controller.update_project(
        project_id=project_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        update_data=request.model_dump(exclude_unset=True),
    )
    return make_success_response(to_project_response(project))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: UUID,
    controller: ProjectCtrl,
    current_user: CurrentUser,
):
    """Archive a project without deleting its historical records."""
    current_user.assert_admin()
    await controller.archive_project(
        project_id=project_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
    )


__all__ = ["router"]
