"""Worker business logic."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.domain.enums import AuditAction, EntityStatus, WorkerStatus
from app.infrastructure.db.models import Department, Project, Worker
from app.repositories.audit import AuditRepository
from app.repositories.worker import WorkerRepository


class WorkerController:
    """Manage workers within organization-scoped departments."""

    def __init__(
        self,
        repository: WorkerRepository,
        audit_repository: AuditRepository | None = None,
    ):
        self.repository = repository
        self.audit_repository = audit_repository

    async def _get_department(self, *, department_id: UUID, organization_id: UUID) -> Department:
        department = await self.repository.session.get(Department, department_id)
        if department is None or department.organization_id != organization_id:
            raise NotFoundError(f"Department '{department_id}' not found")
        project = await self.repository.session.get(Project, department.project_id)
        if project is None or project.organization_id != organization_id:
            raise NotFoundError(f"Project '{department.project_id}' not found")
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived projects cannot contain workers")
        if department.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived departments cannot contain workers")
        return department

    async def create_worker(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        full_name: str,
        phone_number: str,
    ) -> Worker:
        department = await self._get_department(
            department_id=department_id,
            organization_id=organization_id,
        )
        if await self.repository.find_by_phone(
            organization_id=organization_id,
            phone_number=phone_number,
        ):
            raise ConflictError("A worker with this phone number already exists")
        worker = await self.repository.create(
            {
                "organization_id": organization_id,
                "department_id": department.id,
                "full_name": full_name,
                "phone_number": phone_number,
            }
        )
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.CREATE,
            worker=worker,
            metadata={"full_name": worker.full_name, "phone_number": worker.phone_number},
        )
        return worker

    async def list_workers(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Worker], int]:
        await self._get_department(department_id=department_id, organization_id=organization_id)
        return await self.repository.list_in_department(
            department_id=department_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    async def get_worker(self, *, worker_id: UUID, organization_id: UUID) -> Worker:
        worker = await self.repository.get_in_organization(
            worker_id=worker_id,
            organization_id=organization_id,
        )
        if worker is None:
            raise NotFoundError(f"Worker '{worker_id}' not found")
        return worker

    async def update_worker(
        self,
        *,
        worker_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        update_data: dict[str, Any],
    ) -> Worker:
        worker = await self.get_worker(worker_id=worker_id, organization_id=organization_id)
        await self._get_department(
            department_id=worker.department_id, organization_id=organization_id
        )
        if "department_id" in update_data:
            await self._get_department(
                department_id=update_data["department_id"],
                organization_id=organization_id,
            )
        if (
            "phone_number" in update_data
            and update_data["phone_number"] != worker.phone_number
            and await self.repository.find_by_phone(
                organization_id=organization_id,
                phone_number=update_data["phone_number"],
            )
        ):
            raise ConflictError("A worker with this phone number already exists")
        updated = await self.repository.update(worker_id, update_data)
        if updated is None:
            raise NotFoundError(f"Worker '{worker_id}' not found")
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            worker=updated,
            metadata=dict(update_data),
        )
        return updated

    async def assign_worker_to_department(
        self,
        *,
        worker_id: UUID,
        department_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> Worker:
        worker = await self.get_worker(worker_id=worker_id, organization_id=organization_id)
        if worker.status == WorkerStatus.INACTIVE:
            raise UnprocessableEntityError("Inactive workers cannot be assigned")
        target_department = await self._get_department(
            department_id=department_id,
            organization_id=organization_id,
        )
        if worker.department_id == target_department.id:
            raise UnprocessableEntityError("Worker is already assigned to this department")
        previous_department_id = worker.department_id
        updated = await self.repository.update(
            worker.id,
            {"department_id": target_department.id},
        )
        if updated is None:
            raise NotFoundError(f"Worker '{worker_id}' not found")
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            worker=updated,
            metadata={
                "previous_department_id": str(previous_department_id),
                "department_id": str(target_department.id),
                "assignment_action": "assigned",
            },
        )
        return updated

    async def remove_worker_assignment(
        self,
        *,
        worker_id: UUID,
        department_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        worker = await self.get_worker(worker_id=worker_id, organization_id=organization_id)
        await self._get_department(department_id=department_id, organization_id=organization_id)
        if worker.department_id != department_id:
            raise UnprocessableEntityError("Worker is not assigned to this department")
        if worker.status == WorkerStatus.INACTIVE:
            raise UnprocessableEntityError("Worker assignment is already inactive")
        worker.status = WorkerStatus.INACTIVE
        await self.repository.session.commit()
        await self.repository.session.refresh(worker)
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            worker=worker,
            metadata={
                "department_id": str(department_id),
                "status": WorkerStatus.INACTIVE.value,
                "assignment_action": "removed",
            },
        )

    async def archive_worker(
        self,
        *,
        worker_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        worker = await self.get_worker(worker_id=worker_id, organization_id=organization_id)
        worker.status = WorkerStatus.INACTIVE
        await self.repository.session.commit()
        await self.repository.session.refresh(worker)
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            worker=worker,
            metadata={"status": WorkerStatus.INACTIVE.value},
        )

    async def _audit(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        action: AuditAction,
        worker: Worker,
        metadata: dict[str, Any],
    ) -> None:
        if self.audit_repository is not None:
            await self.audit_repository.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type="worker",
                resource_id=worker.id,
                metadata=metadata,
            )


__all__ = ["WorkerController"]
