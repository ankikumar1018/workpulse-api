from datetime import timedelta
from uuid import uuid4

import pytest

from app.api.dependencies import get_auth_context
from app.api.errors import UnauthorizedError
from app.api.security import create_access_token, decode_access_token


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
        await get_auth_context(None)

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

    auth_context = await get_auth_context(token)

    assert auth_context.user_id == user_id
    assert auth_context.organization_id == organization_id
    assert auth_context.role == "viewer"
