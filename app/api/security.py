"""JWT access-token creation and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import cast
from uuid import UUID, uuid4

import bcrypt
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


def create_refresh_token(
    *,
    user_id: UUID,
    organization_id: UUID,
    role: str = "admin",
) -> str:
    """Create a signed refresh token with a revocable session identifier."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "organization_id": str(organization_id),
        "role": role,
        "type": "refresh",
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return cast(
        str,
        jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM),
    )


def decode_refresh_token(token: str) -> dict[str, str]:
    """Decode and validate a refresh token's required claims."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        user_id = UUID(str(payload["sub"]))
        organization_id = UUID(str(payload["organization_id"]))
        role = str(payload["role"])
        jti = str(payload["jti"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid refresh token") from exc

    return {
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "role": role,
        "jti": jti,
        "type": "refresh",
    }


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_digest = sha256(password.encode("utf-8")).digest()
    return bcrypt.hashpw(password_digest, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its stored hash."""
    try:
        password_digest = sha256(password.encode("utf-8")).digest()
        return bcrypt.checkpw(password_digest, password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token before persistence or lookup."""
    return sha256(token.encode("utf-8")).hexdigest()


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "hash_password",
    "hash_refresh_token",
    "verify_password",
]
