from datetime import timedelta
from uuid import uuid4

import pytest

from app.api.dependencies import AuthContext, get_auth_context
from app.api.errors import ForbiddenError, UnauthorizedError
from app.api.security import create_access_token, decode_access_token
from app.infrastructure.db.models import User


class FakeSession:
    def __init__(self, user: User | None):
        self.user = user

    async def get(self, _model, user_id):
        return self.user if self.user and self.user.id == user_id else None


def test_access_token_round_trip():
    user_id = uuid4()
    organization_id = uuid4()

    token = create_access_token(
        user_id=user_id,
        organization_id=organization_id,
        role="admin",
    )

    assert decode_access_token(token) == {
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "role": "admin",
    }


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        create_access_token(
            user_id=uuid4(),
            organization_id=uuid4(),
            expires_delta=timedelta(seconds=-1),
        ),
    ],
)
def test_decode_access_token_rejects_invalid_tokens(token):
    with pytest.raises(ValueError, match="Invalid access token"):
        decode_access_token(token)


@pytest.mark.asyncio
async def test_auth_context_requires_bearer_token():
    with pytest.raises(UnauthorizedError) as exception_info:
        await get_auth_context(None, FakeSession(None))

    assert exception_info.value.status_code == 401
    assert exception_info.value.message == "Missing bearer token"
    assert exception_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_auth_context_uses_token_claims():
    user_id = uuid4()
    organization_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        organization_id=organization_id,
        role="viewer",
    )

    auth_context = await get_auth_context(
        token,
        FakeSession(
            User(
                id=user_id,
                organization_id=organization_id,
                email="admin@example.com",
                password_hash="unused",
                role="viewer",
                status="active",
            )
        ),
    )

    assert auth_context.user_id == user_id
    assert auth_context.organization_id == organization_id
    assert auth_context.role == "viewer"


@pytest.mark.asyncio
async def test_auth_context_rejects_inactive_user():
    user_id = uuid4()
    organization_id = uuid4()
    token = create_access_token(user_id=user_id, organization_id=organization_id)

    with pytest.raises(UnauthorizedError) as exception_info:
        await get_auth_context(
            token,
            FakeSession(
                User(
                    id=user_id,
                    organization_id=organization_id,
                    email="admin@example.com",
                    password_hash="unused",
                    role="admin",
                    status="inactive",
                )
            ),
        )

    assert exception_info.value.message == "User is inactive or does not exist"


@pytest.mark.asyncio
async def test_auth_context_uses_current_database_role():
    user_id = uuid4()
    organization_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        organization_id=organization_id,
        role="admin",
    )

    auth_context = await get_auth_context(
        token,
        FakeSession(
            User(
                id=user_id,
                organization_id=organization_id,
                email="user@example.com",
                password_hash="unused",
                role="viewer",
                status="active",
            )
        ),
    )

    assert auth_context.role == "viewer"


def test_non_admin_auth_context_is_forbidden_from_admin_operations():
    context = AuthContext(user_id=uuid4(), organization_id=uuid4(), role="viewer")

    with pytest.raises(ForbiddenError) as exception_info:
        context.assert_admin()

    assert exception_info.value.message == "Admin role required"
