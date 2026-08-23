"""Authentication application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.api.errors import UnauthorizedError
from app.api.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
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
