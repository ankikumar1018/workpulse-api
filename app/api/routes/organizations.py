"""Organization API endpoints (WI-2.3, WI-2.4)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.api.errors import ConflictError, NotFoundError
from app.api.schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.infrastructure.db.models import Organization
from app.infrastructure.db.session import get_db_session

router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Organizations"],
)

DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="Create organization",
)
async def create_organization(
    request: OrganizationCreateRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new organization.

    Only admin users can create organizations.
    """
    current_user.assert_admin()

    # Check if slug already exists
    existing = await db.execute(
        select(Organization).where(Organization.slug == request.slug)
    )
    if existing.scalars().first():
        raise ConflictError(f"Organization with slug '{request.slug}' already exists")

    # Create organization
    org = Organization(
        name=request.name,
        slug=request.slug,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)

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
    response_model=dict,
    summary="List organizations",
)
async def list_organizations(
    db: DBSession,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    status: str | None = Query(None),
):
    """
    List organizations (paginated).

    Only admin users can list all organizations.
    Non-admin users would be restricted to their own organization (Phase 2).
    """
    current_user.assert_admin()

    limit, offset = parse_pagination_params(limit, offset)

    # Build query
    query = select(Organization)
    if status:
        query = query.where(Organization.status == status)

    # Get total count
    count_result = await db.execute(select(func.count(Organization.id)).select_from(Organization))
    total = count_result.scalars().first() or 0

    # Get paginated results
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    organizations = result.scalars().all()

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
    response_model=dict,
    summary="Get organization details",
)
async def get_organization(
    org_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Retrieve a specific organization by ID.

    Enforces organization scoping for non-admin users (Phase 2).
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalars().first()

    if not org:
        raise NotFoundError(f"Organization '{org_id}' not found")

    # Enforce organization boundary
    current_user.assert_organization(org_id)

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
    response_model=dict,
    summary="Update organization",
)
async def update_organization(
    org_id: UUID,
    request: OrganizationUpdateRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Partially update an organization.

    Only admin users can update organizations.
    """
    current_user.assert_admin()
    current_user.assert_organization(org_id)

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalars().first()

    if not org:
        raise NotFoundError(f"Organization '{org_id}' not found")

    # Update fields if provided
    if request.name is not None:
        org.name = request.name
    if request.status is not None:
        org.status = request.status
    if request.subscription_status is not None:
        org.subscription_status = request.subscription_status

    await db.commit()
    await db.refresh(org)

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
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Delete an organization (hard delete).

    Only admin users can delete organizations.
    WARNING: This is permanent and will cascade to all related data.
    """
    current_user.assert_admin()
    current_user.assert_organization(org_id)

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalars().first()

    if not org:
        raise NotFoundError(f"Organization '{org_id}' not found")

    await db.delete(org)
    await db.commit()


__all__ = ["router"]
