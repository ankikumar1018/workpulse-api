"""JWT access-token creation and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from jose import JWTError, jwt

from core.config import settings


def create_access_token(
    *,
    user_id: UUID,
    organization_id: UUID,
    role: str = "admin",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed access token for an authenticated user."""
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(user_id),
        "organization_id": str(organization_id),
        "role": role,
        "type": "access",
        "jti": str(uuid4()),
        "iat": now,
        "exp": expires_at,
    }
    return cast(
        str,
        jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM),
    )


def decode_access_token(token: str) -> dict[str, str]:
    """Decode and validate an access token's required claims."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")

        user_id = UUID(str(payload["sub"]))
        organization_id = UUID(str(payload["organization_id"]))
        role = str(payload["role"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid access token") from exc

    return {
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "role": role,
    }


__all__ = ["create_access_token", "decode_access_token"]
