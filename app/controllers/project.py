"""Project business logic."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.domain.enums import AuditAction, EntityStatus
from app.infrastructure.db.models import Project
from app.repositories.audit import AuditRepository
from app.repositories.project import ProjectRepository


class ProjectController:
    """Manage projects within an organization."""

    def __init__(
        self,
        repository: ProjectRepository,
        audit_repository: AuditRepository | None = None,
    ):
        self.repository = repository
        self.audit_repository = audit_repository

    async def create_project(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        name: str,
        description: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> Project:
        if await self.repository.find_by_name(organization_id=organization_id, name=name):
            raise ConflictError("A project with this name already exists")
        project = await self.repository.create(
            {
                "organization_id": organization_id,
                "name": name,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.CREATE,
            project=project,
            metadata={"name": project.name},
        )
        return project

    async def list_projects(
        self,
        *,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Project], int]:
        return await self.repository.list_in_organization(
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    async def get_project(self, *, project_id: UUID, organization_id: UUID) -> Project:
        project = await self.repository.get_in_organization(
            project_id=project_id,
            organization_id=organization_id,
        )
        if project is None:
            raise NotFoundError(f"Project '{project_id}' not found")
        return project

    async def update_project(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        update_data: dict[str, Any],
    ) -> Project:
        project = await self.get_project(project_id=project_id, organization_id=organization_id)
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived projects cannot be modified")
        if (
            "name" in update_data
            and update_data["name"] != project.name
            and await self.repository.find_by_name(
                organization_id=organization_id,
                name=update_data["name"],
            )
        ):
            raise ConflictError("A project with this name already exists")
        start_date = update_data.get("start_date", project.start_date)
        end_date = update_data.get("end_date", project.end_date)
        if start_date and end_date and end_date < start_date:
            raise UnprocessableEntityError("end_date must be on or after start_date")
        updated = await self.repository.update(project_id, update_data)
        if updated is None:
            raise NotFoundError(f"Project '{project_id}' not found")
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            project=updated,
            metadata={key: value for key, value in update_data.items() if key != "password"},
        )
        return updated

    async def archive_project(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        project = await self.get_project(project_id=project_id, organization_id=organization_id)
        if project.status == EntityStatus.ARCHIVED:
            return
        project.status = EntityStatus.ARCHIVED
        await self.repository.session.commit()
        await self.repository.session.refresh(project)
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            project=project,
            metadata={"status": EntityStatus.ARCHIVED.value},
        )

    async def _audit(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        action: AuditAction,
        project: Project,
        metadata: dict[str, Any],
    ) -> None:
        if self.audit_repository is not None:
            await self.audit_repository.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type="project",
                resource_id=project.id,
                metadata=metadata,
            )


__all__ = ["ProjectController"]
