"""Repository for append-only work item status history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import WorkItemStatusHistory


class WorkItemStatusHistoryRepository:
    """Persist and query append-only work item status transitions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        organization_id: UUID,
        work_item_id: UUID,
        previous_status: Any,
        new_status: Any,
        actor_user_id: UUID | None,
        reason: str | None = None,
    ) -> WorkItemStatusHistory:
        """Store a single status transition in append-only history."""
        record = WorkItemStatusHistory(
            organization_id=organization_id,
            work_item_id=work_item_id,
            previous_status=previous_status,
            new_status=new_status,
            actor_user_id=actor_user_id,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_for_work_item(
        self,
        *,
        work_item_id: UUID,
        organization_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[WorkItemStatusHistory], int]:
        """Return ordered status history for a specific work item."""
        statement = (
            select(WorkItemStatusHistory)
            .where(
                WorkItemStatusHistory.work_item_id == work_item_id,
                WorkItemStatusHistory.organization_id == organization_id,
            )
            .order_by(WorkItemStatusHistory.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        rows = list(result.scalars().all())

        count_statement = select(WorkItemStatusHistory).where(
            WorkItemStatusHistory.work_item_id == work_item_id,
            WorkItemStatusHistory.organization_id == organization_id,
        )
        count_result = await self.session.execute(count_statement)
        total = len(count_result.scalars().all())
        return rows, total


__all__ = ["WorkItemStatusHistoryRepository"]
