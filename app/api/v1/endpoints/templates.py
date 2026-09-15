"""Message template API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, TemplateSvc
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.domain.enums import Channel
from app.infrastructure.db.models import Template
from app.schemas import (
    ListEnvelope,
    SuccessEnvelope,
    TemplateCreateRequest,
    TemplateResponse,
    TemplateUpdateRequest,
)

router = APIRouter(tags=["Templates"])


def to_template_response(template: Template) -> TemplateResponse:
    """Convert a template ORM object to its public response representation."""
    return TemplateResponse(
        id=template.id,
        organization_id=template.organization_id,
        project_id=template.project_id,
        name=template.name,
        channel=template.channel.value,
        body=template.body,
        variable_schema=template.variable_schema_json or {},
        status=template.status.value,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post(
    "/projects/{project_id}/templates",
    response_model=SuccessEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    project_id: UUID,
    request: TemplateCreateRequest,
    controller: TemplateSvc,
    current_user: CurrentUser,
):
    """Create a tenant-scoped template in a project."""
    current_user.assert_admin()
    template = await controller.create_template(
        organization_id=current_user.organization_id,
        project_id=project_id,
        actor_user_id=current_user.user_id,
        name=request.name,
        channel=Channel(request.channel),
        body=request.body,
        variable_schema=request.variable_schema,
    )
    return make_success_response(to_template_response(template))


@router.get("/projects/{project_id}/templates", response_model=ListEnvelope)
async def list_templates(
    project_id: UUID,
    controller: TemplateSvc,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    template_status: str | None = Query(None, alias="status"),
):
    """List templates in a project belonging to the current organization."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    templates, total = await controller.list_templates(
        project_id=project_id,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        status=template_status,
    )
    return make_list_response(
        [to_template_response(template) for template in templates], total, limit, offset
    )


@router.get("/templates/{template_id}", response_model=SuccessEnvelope)
async def get_template(
    template_id: UUID,
    controller: TemplateSvc,
    current_user: CurrentUser,
):
    """Get a template from the current user's organization."""
    current_user.assert_admin()
    template = await controller.get_template(
        template_id=template_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response(to_template_response(template))


@router.patch("/templates/{template_id}", response_model=SuccessEnvelope)
async def update_template(
    template_id: UUID,
    request: TemplateUpdateRequest,
    controller: TemplateSvc,
    current_user: CurrentUser,
):
    """Update an active template in the current user's organization."""
    current_user.assert_admin()
    update_data = request.model_dump(exclude_unset=True)
    if "channel" in update_data:
        update_data["channel"] = Channel(update_data["channel"])
    if "variable_schema" in update_data:
        update_data["variable_schema_json"] = update_data.pop("variable_schema")
    template = await controller.update_template(
        template_id=template_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        update_data=update_data,
    )
    return make_success_response(to_template_response(template))


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_template(
    template_id: UUID,
    controller: TemplateSvc,
    current_user: CurrentUser,
):
    """Archive a template without deleting its historical configuration."""
    current_user.assert_admin()
    await controller.archive_template(
        template_id=template_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
    )


__all__ = ["router"]
