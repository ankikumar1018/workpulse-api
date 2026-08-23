from uuid import uuid4

import pytest

from app.api.errors import ConflictError, NotFoundError, UnauthorizedError
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
        self.users = [user]
        self.refresh_session: RefreshSession | None = None
        self.database_session = FakeDatabaseSession()

    async def get_user_by_email(self, email: str):
        return next((user for user in self.users if email.lower() == user.email), None)

    async def get_user(self, user_id):
        return next((user for user in self.users if user_id == user.id), None)

    async def create_user(self, user):
        self.users.append(user)
        return user

    async def list_users(self, *, organization_id, limit, offset):
        users = [user for user in self.users if user.organization_id == organization_id]
        return users[offset : offset + limit], len(users)

    async def get_user_in_organization(self, *, user_id, organization_id):
        return next(
            (
                user
                for user in self.users
                if user.id == user_id and user.organization_id == organization_id
            ),
            None,
        )

    async def get_refresh_session(self, token_hash: str):
        return (
            self.refresh_session
            if self.refresh_session and self.refresh_session.token_hash == token_hash
            else None
        )

    async def create_refresh_session(self, *, user_id, token_hash, expires_at):
        self.refresh_session = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return self.session

    async def revoke_refresh_session(self, session, now):
        session.revoked_at = now

    @property
    def session(self):
        return self.database_session


class FakeDatabaseSession:
    async def commit(self):
        pass

    async def refresh(self, _user):
        pass


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
    old_session = repository.refresh_session

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


@pytest.mark.asyncio
async def test_user_lifecycle_normalizes_email_and_hashes_password():
    organization_id = uuid4()
    user = make_user()
    user.organization_id = organization_id
    repository = FakeAuthRepository(user)
    controller = AuthController(repository)

    created = await controller.create_user(
        organization_id=organization_id,
        email="  NEW@EXAMPLE.COM ",
        password="new-password",
        role="admin",
        status="active",
    )

    assert created.email == "new@example.com"
    assert created.password_hash != "new-password"
    assert verify_password("new-password", created.password_hash)

    updated = await controller.update_user(
        user_id=created.id,
        organization_id=organization_id,
        password="updated-password",
        status="inactive",
    )

    assert updated.status == "inactive"
    assert verify_password("updated-password", updated.password_hash)
    with pytest.raises(UnauthorizedError) as exception_info:
        await controller.login(created.email, "updated-password")
    assert exception_info.value.message == "Invalid email or password"


@pytest.mark.asyncio
async def test_user_management_rejects_duplicate_and_cross_organization_access():
    user = make_user()
    repository = FakeAuthRepository(user)
    controller = AuthController(repository)

    with pytest.raises(ConflictError) as exception_info:
        await controller.create_user(
            organization_id=user.organization_id,
            email=user.email,
            password="another-password",
            role="admin",
            status="active",
        )
    assert exception_info.value.message == "A user with this email already exists"

    with pytest.raises(NotFoundError) as exception_info:
        await controller.get_user(user_id=user.id, organization_id=uuid4())
    assert exception_info.value.message == f"User '{user.id}' not found"
