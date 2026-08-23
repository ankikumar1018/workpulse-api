"""Department business logic."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.domain.enums import AuditAction, EntityStatus, WorkerStatus
from app.infrastructure.db.models import Department, Project, Worker
from app.repositories.audit import AuditRepository
from app.repositories.department import DepartmentRepository


class DepartmentController:
    """Manage departments within organization-scoped projects."""

    def __init__(
        self,
        repository: DepartmentRepository,
        audit_repository: AuditRepository | None = None,
    ):
        self.repository = repository
        self.audit_repository = audit_repository

    async def _get_project(self, *, project_id: UUID, organization_id: UUID) -> Project:
        project = await self.repository.session.get(Project, project_id)
        if project is None or project.organization_id != organization_id:
            raise NotFoundError(f"Project '{project_id}' not found")
        return project

    async def _validate_primary_contact_worker(
        self,
        *,
        worker_id: UUID,
        department: Department,
        organization_id: UUID,
    ) -> Worker:
        worker = await self.repository.session.get(Worker, worker_id)
        if worker is None or worker.organization_id != organization_id:
            raise NotFoundError(f"Worker '{worker_id}' not found")
        if worker.department_id != department.id:
            raise UnprocessableEntityError(
                "Primary contact worker must belong to the same department"
            )
        if worker.status == WorkerStatus.INACTIVE:
            raise UnprocessableEntityError("Inactive workers cannot be primary contacts")
        return worker

    async def create_department(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        name: str,
    ) -> Department:
        project = await self._get_project(project_id=project_id, organization_id=organization_id)
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived projects cannot contain new departments")
        if await self.repository.find_by_name(project_id=project_id, name=name):
            raise ConflictError("A department with this name already exists")
        department = await self.repository.create(
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "name": name,
            }
        )
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.CREATE,
            department=department,
            metadata={"name": department.name, "project_id": str(project_id)},
        )
        return department

    async def list_departments(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Department], int]:
        await self._get_project(project_id=project_id, organization_id=organization_id)
        return await self.repository.list_in_project(
            project_id=project_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    async def get_department(self, *, department_id: UUID, organization_id: UUID) -> Department:
        department = await self.repository.get_in_organization(
            department_id=department_id,
            organization_id=organization_id,
        )
        if department is None:
            raise NotFoundError(f"Department '{department_id}' not found")
        return department

    async def update_department(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        update_data: dict[str, Any],
    ) -> Department:
        department = await self.get_department(
            department_id=department_id,
            organization_id=organization_id,
        )
        project = await self._get_project(
            project_id=department.project_id,
            organization_id=organization_id,
        )
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived projects cannot be modified")
        if (
            "name" in update_data
            and update_data["name"] != department.name
            and await self.repository.find_by_name(
                project_id=department.project_id,
                name=update_data["name"],
            )
        ):
            raise ConflictError("A department with this name already exists")
        if "primary_contact_worker_id" in update_data:
            primary_contact_worker_id = update_data["primary_contact_worker_id"]
            if department.status == EntityStatus.ARCHIVED and primary_contact_worker_id is not None:
                raise UnprocessableEntityError(
                    "Archived departments cannot have active primary contacts"
                )
            if primary_contact_worker_id is not None:
                await self._validate_primary_contact_worker(
                    worker_id=primary_contact_worker_id,
                    department=department,
                    organization_id=organization_id,
                )
        updated = await self.repository.update(department_id, update_data)
        if updated is None:
            raise NotFoundError(f"Department '{department_id}' not found")
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            department=updated,
            metadata=dict(update_data),
        )
        return updated

    async def archive_department(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        department = await self.get_department(
            department_id=department_id,
            organization_id=organization_id,
        )
        department.status = EntityStatus.ARCHIVED
        department.primary_contact_worker_id = None
        await self.repository.session.commit()
        await self.repository.session.refresh(department)
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            department=department,
            metadata={
                "status": EntityStatus.ARCHIVED.value,
                "primary_contact_worker_id": None,
            },
        )

    async def _audit(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        action: AuditAction,
        department: Department,
        metadata: dict[str, Any],
    ) -> None:
        if self.audit_repository is not None:
            await self.audit_repository.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type="department",
                resource_id=department.id,
                metadata=metadata,
            )


__all__ = ["DepartmentController"]
