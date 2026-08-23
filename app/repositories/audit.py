"""Audit log persistence operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.infrastructure.db.models import AuditLog


class AuditRepository:
    """Persist append-only administrative audit records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID | None,
        action: AuditAction,
        resource_type: str,
        resource_id: UUID | None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Record an audit event without exposing sensitive request data."""
        audit_log = AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata,
        )
        self.session.add(audit_log)
        await self.session.commit()
        await self.session.refresh(audit_log)
        return audit_log


__all__ = ["AuditRepository"]
