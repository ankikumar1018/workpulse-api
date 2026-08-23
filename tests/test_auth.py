from uuid import uuid4

import pytest

from app.api.errors import UnauthorizedError
from app.api.security import (
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.controllers.auth import AuthController
from app.infrastructure.db.models import RefreshSession, User


class FakeAuthRepository:
    def __init__(self, user: User):
        self.user = user
        self.session: RefreshSession | None = None

    async def get_user_by_email(self, email: str):
        return self.user if email.lower() == self.user.email else None

    async def get_user(self, user_id):
        return self.user if user_id == self.user.id else None

    async def get_refresh_session(self, token_hash: str):
        return self.session if self.session and self.session.token_hash == token_hash else None

    async def create_refresh_session(self, *, user_id, token_hash, expires_at):
        self.session = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return self.session

    async def revoke_refresh_session(self, session, now):
        session.revoked_at = now


def make_user() -> User:
    return User(
        id=uuid4(),
        organization_id=uuid4(),
        email="admin@example.com",
        password_hash=hash_password("correct-password"),
        role="admin",
        status="active",
    )


def test_refresh_token_round_trip():
    user_id = uuid4()
    organization_id = uuid4()

    token = create_refresh_token(user_id=user_id, organization_id=organization_id)

    claims = decode_refresh_token(token)
    assert claims["user_id"] == str(user_id)
    assert claims["organization_id"] == str(organization_id)
    assert claims["type"] == "refresh"
    assert claims["jti"]
    assert hash_refresh_token(token) != token


def test_password_hashing():
    password_hash = hash_password("secret")

    assert password_hash != "secret"
    assert verify_password("secret", password_hash)
    assert not verify_password("wrong", password_hash)
    assert verify_password("x" * 100, hash_password("x" * 100))


@pytest.mark.asyncio
async def test_login_issues_tokens_and_refresh_rotates_session():
    user = make_user()
    repository = FakeAuthRepository(user)
    controller = AuthController(repository)

    tokens = await controller.login(user.email, "correct-password")
    old_session = repository.session

    assert tokens.token_type == "bearer"
    assert tokens.access_token
    assert tokens.refresh_token
    assert old_session is not None

    rotated = await controller.refresh(tokens.refresh_token)

    assert rotated.refresh_token != tokens.refresh_token
    assert old_session.revoked_at is not None


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials():
    controller = AuthController(FakeAuthRepository(make_user()))

    with pytest.raises(UnauthorizedError):
        await controller.login("admin@example.com", "wrong-password")


@pytest.mark.asyncio
async def test_refresh_rejects_revoked_session():
    user = make_user()
    repository = FakeAuthRepository(user)
    controller = AuthController(repository)
    tokens = await controller.login(user.email, "correct-password")
    await controller.refresh(tokens.refresh_token)

    with pytest.raises(UnauthorizedError):
        await controller.refresh(tokens.refresh_token)
