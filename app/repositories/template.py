"""Template persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Channel
from app.infrastructure.db.models import Template
from app.infrastructure.repository import BaseRepository


class TemplateRepository(BaseRepository[Template]):
    """Tenant-scoped message template repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Template)

    async def find_by_name(
        self,
        *,
        project_id: UUID,
        name: str,
        channel: Channel,
    ) -> Template | None:
        result = await self.session.execute(
            select(Template).where(
                Template.project_id == project_id,
                Template.name == name,
                Template.channel == channel,
            )
        )
        return result.scalar_one_or_none()

    async def get_in_organization(
        self,
        *,
        template_id: UUID,
        organization_id: UUID,
    ) -> Template | None:
        result = await self.session.execute(
            select(Template).where(
                Template.id == template_id,
                Template.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_project(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Template], int]:
        filters: dict[str, object] = {
            "project_id": project_id,
            "organization_id": organization_id,
        }
        if status:
            filters["status"] = status
        return await self.find_all(limit=limit, offset=offset, **filters)


__all__ = ["TemplateRepository"]
