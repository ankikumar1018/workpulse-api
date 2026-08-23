"""Organization API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, OrganizationCtrl
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.schemas import (
    ListEnvelope,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    SuccessEnvelope,
)

router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Organizations"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope,
    summary="Create organization",
)
async def create_organization(
    request: OrganizationCreateRequest,
    controller: OrganizationCtrl,
    current_user: CurrentUser,
):
    """Create a new organization."""
    current_user.assert_admin()
    org = await controller.create_organization(
        name=request.name,
        slug=request.slug,
    )

    response = OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status.value,
        subscription_status=org.subscription_status.value if org.subscription_status else None,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )
    return make_success_response(response)


@router.get(
    "",
    response_model=ListEnvelope,
    summary="List organizations",
)
async def list_organizations(
    controller: OrganizationCtrl,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    status: str | None = Query(None),
):
    """List organizations (paginated)."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)

    organizations, total = await controller.list_organizations(
        limit=limit,
        offset=offset,
        status=status,
    )

    data = [
        OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            status=org.status.value,
            subscription_status=org.subscription_status.value if org.subscription_status else None,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )
        for org in organizations
    ]

    return make_list_response(data, total, limit, offset)


@router.get(
    "/{org_id}",
    response_model=SuccessEnvelope,
    summary="Get organization details",
)
async def get_organization(
    org_id: UUID,
    controller: OrganizationCtrl,
    current_user: CurrentUser,
):
    """Retrieve a specific organization by ID."""
    current_user.assert_organization(org_id)
    org = await controller.get_organization(org_id)

    response = OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status.value,
        subscription_status=org.subscription_status.value if org.subscription_status else None,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )
    return make_success_response(response)


@router.patch(
    "/{org_id}",
    response_model=SuccessEnvelope,
    summary="Update organization",
)
async def update_organization(
    org_id: UUID,
    request: OrganizationUpdateRequest,
    controller: OrganizationCtrl,
    current_user: CurrentUser,
):
    """Partially update an organization."""
    current_user.assert_admin()
    current_user.assert_organization(org_id)
    update_data = request.model_dump(exclude_unset=True)
    org = await controller.update_organization(org_id, update_data)

    response = OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status.value,
        subscription_status=org.subscription_status.value if org.subscription_status else None,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )
    return make_success_response(response)


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization",
)
async def delete_organization(
    org_id: UUID,
    controller: OrganizationCtrl,
    current_user: CurrentUser,
):
    """Delete an organization."""
    current_user.assert_admin()
    current_user.assert_organization(org_id)
    await controller.delete_organization(org_id)


__all__ = ["router"]
