"""Authentication application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.api.errors import ConflictError, NotFoundError, UnauthorizedError
from app.api.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.infrastructure.db.models import User
from app.repositories.auth import AuthRepository
from app.schemas.responses.auth import TokenResponse
from core.config import settings


class AuthController:
    """Authenticate users and rotate refresh sessions."""

    def __init__(self, repository: AuthRepository):
        self.repository = repository

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repository.get_user_by_email(email)
        if (
            user is None
            or user.status != "active"
            or not verify_password(password, user.password_hash)
        ):
            raise UnauthorizedError("Invalid email or password")
        return await self._issue_tokens(user)

    async def create_user(
        self,
        *,
        organization_id: UUID,
        email: str,
        password: str,
        role: str,
        status: str,
    ) -> User:
        normalized_email = email.strip().lower()
        if await self.repository.get_user_by_email(normalized_email):
            raise ConflictError("A user with this email already exists")

        return await self.repository.create_user(
            User(
                organization_id=organization_id,
                email=normalized_email,
                password_hash=hash_password(password),
                role=role,
                status=status,
            )
        )

    async def list_users(
        self,
        *,
        organization_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[User], int]:
        return await self.repository.list_users(
            organization_id=organization_id,
            limit=limit,
            offset=offset,
        )

    async def get_user(self, *, user_id: UUID, organization_id: UUID) -> User:
        user = await self.repository.get_user_in_organization(
            user_id=user_id,
            organization_id=organization_id,
        )
        if user is None:
            raise NotFoundError(f"User '{user_id}' not found")
        return user

    async def update_user(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        email: str | None = None,
        password: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> User:
        user = await self.get_user(user_id=user_id, organization_id=organization_id)
        if email is not None:
            normalized_email = email.strip().lower()
            existing = await self.repository.get_user_by_email(normalized_email)
            if existing is not None and existing.id != user.id:
                raise ConflictError("A user with this email already exists")
            user.email = normalized_email
        if password is not None:
            user.password_hash = hash_password(password)
        if role is not None:
            user.role = role
        if status is not None:
            user.status = status
        await self.repository.session.commit()
        await self.repository.session.refresh(user)
        return user

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            claims = decode_refresh_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        session = await self.repository.get_refresh_session(hash_refresh_token(refresh_token))
        now = datetime.now(UTC)
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise UnauthorizedError("Refresh session is invalid or expired")

        user = await self.repository.get_user(session.user_id)
        if user is None or user.status != "active" or str(user.id) != claims["user_id"]:
            raise UnauthorizedError("User is not active")

        await self.repository.revoke_refresh_session(session, now)
        return await self._issue_tokens(user)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
        )
        decode_refresh_token(refresh_token)
        await self.repository.create_refresh_session(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )


__all__ = ["AuthController"]
