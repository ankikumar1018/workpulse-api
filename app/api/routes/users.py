"""Administrator user management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import AuthCtrl, CurrentUser
from app.api.utils import make_list_response, make_success_response, parse_pagination_params
from app.infrastructure.db.models import User
from app.schemas import (
    ListEnvelope,
    SuccessEnvelope,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


def to_user_response(user: User) -> UserResponse:
    """Convert an ORM user to its public response representation."""
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("", response_model=SuccessEnvelope, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    controller: AuthCtrl,
    current_user: CurrentUser,
):
    """Create an administrator in the current user's organization."""
    current_user.assert_admin()
    user = await controller.create_user(
        organization_id=current_user.organization_id,
        email=request.email,
        password=request.password,
        role=request.role,
        status=request.status,
    )
    return make_success_response(to_user_response(user))


@router.get("", response_model=ListEnvelope)
async def list_users(
    controller: AuthCtrl,
    current_user: CurrentUser,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    """List users in the current user's organization."""
    current_user.assert_admin()
    limit, offset = parse_pagination_params(limit, offset)
    users, total = await controller.list_users(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )
    return make_list_response([to_user_response(user) for user in users], total, limit, offset)


@router.get("/{user_id}", response_model=SuccessEnvelope)
async def get_user(
    user_id: UUID,
    controller: AuthCtrl,
    current_user: CurrentUser,
):
    """Get a user from the current user's organization."""
    current_user.assert_admin()
    user = await controller.get_user(
        user_id=user_id,
        organization_id=current_user.organization_id,
    )
    return make_success_response(to_user_response(user))


@router.patch("/{user_id}", response_model=SuccessEnvelope)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    controller: AuthCtrl,
    current_user: CurrentUser,
):
    """Update a user in the current user's organization."""
    current_user.assert_admin()
    user = await controller.update_user(
        user_id=user_id,
        organization_id=current_user.organization_id,
        **request.model_dump(exclude_unset=True),
    )
    return make_success_response(to_user_response(user))


__all__ = ["router"]
