"""Work item business logic and orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.enums import AuditAction, EntityStatus, WorkerStatus, WorkPriority, WorkStatus
from app.domain.work_item import InvalidTransitionError, WorkItemStateTransition
from app.infrastructure.db.models import Department, Project, Worker, WorkItem as WorkItemModel
from app.repositories.audit import AuditRepository
from app.repositories.work_item import WorkItemRepository
from app.repositories.work_item_status_history import WorkItemStatusHistoryRepository


class WorkItemService:
    """Manage work items within organization and project scopes."""

    def __init__(
        self,
        repository: WorkItemRepository,
        audit_repository: AuditRepository | None = None,
        status_history_repository: WorkItemStatusHistoryRepository | None = None,
    ):
        self.repository = repository
        self.audit_repository = audit_repository
        self.status_history_repository = status_history_repository

    async def _get_project(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
    ) -> Project:
        """Get and validate project access.

        Args:
            project_id: Project ID
            organization_id: Organization ID

        Returns:
            The project if found and scoped correctly

        Raises:
            NotFoundError: If project not found or not accessible
        """
        project = await self.repository.session.get(Project, project_id)
        if project is None or project.organization_id != organization_id:
            raise NotFoundError(f"Project '{project_id}' not found")
        return project

    async def _get_department(
        self,
        *,
        department_id: UUID,
        organization_id: UUID,
    ) -> Department:
        """Get and validate department access.

        Args:
            department_id: Department ID
            organization_id: Organization ID

        Returns:
            The department if found and scoped correctly

        Raises:
            NotFoundError: If department not found or not accessible
        """
        department = await self.repository.session.get(Department, department_id)
        if department is None or department.organization_id != organization_id:
            raise NotFoundError(f"Department '{department_id}' not found")
        return department

    async def _audit(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID | None,
        action: AuditAction,
        resource_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an audit log for a work item action.

        Args:
            organization_id: Organization ID
            actor_user_id: User performing the action
            action: Type of action
            resource_id: Work item ID
            metadata: Additional context
        """
        if self.audit_repository:
            await self.audit_repository.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type="work_item",
                resource_id=resource_id,
                metadata=metadata,
            )

    async def create_work_item(
        self,
        *,
        project_id: UUID,
        department_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID | None,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        worker_id: UUID | None = None,
        due_at: datetime | None = None,
    ) -> WorkItemModel:
        """Create a new work item in a project and department.

        Args:
            project_id: Project ID
            department_id: Department ID
            organization_id: Organization ID
            actor_user_id: User creating the work item
            title: Work item title
            description: Optional work item description
            priority: Work item priority level
            worker_id: Optional assigned worker ID

        Returns:
            The created work item

        Raises:
            NotFoundError: If project or department not found
            UnprocessableEntityError: If archived or invalid relationships
        """
        # Validate project
        project = await self._get_project(project_id=project_id, organization_id=organization_id)
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Cannot create work items in archived projects")

        # Validate department
        department = await self._get_department(
            department_id=department_id,
            organization_id=organization_id,
        )
        if department.project_id != project_id:
            raise UnprocessableEntityError(
                f"Department '{department_id}' does not belong to project '{project_id}'"
            )
        if department.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Cannot create work items in archived departments")

        if worker_id is not None:
            worker = await self.repository.session.get(Worker, worker_id)
            if worker is None or worker.organization_id != organization_id:
                raise NotFoundError(f"Worker '{worker_id}' not found")
            if worker.department_id != department_id:
                raise UnprocessableEntityError(
                    f"Worker '{worker_id}' does not belong to department '{department_id}'"
                )
            if worker.status == WorkerStatus.INACTIVE:
                raise UnprocessableEntityError("Inactive workers cannot be assigned work items")

        try:
            priority_enum = WorkPriority(priority)
        except ValueError as error:
            raise UnprocessableEntityError(f"Invalid priority '{priority}'") from error

        # Create the work item
        work_item = await self.repository.create(
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "department_id": department_id,
                "worker_id": worker_id,
                "title": title,
                "description": description,
                "priority": priority_enum,
                "status": WorkStatus.OPEN,
                "due_at": due_at,
                "created_by_user_id": actor_user_id,
            }
        )

        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.CREATE,
            resource_id=work_item.id,
            metadata={
                "title": work_item.title,
                "priority": work_item.priority.value,
                "status": work_item.status.value,
                "department_id": str(department_id),
                "project_id": str(project_id),
            },
        )

        return work_item

    async def _record_status_history(
        self,
        *,
        work_item: WorkItemModel,
        previous_status: WorkStatus,
        new_status: WorkStatus,
        organization_id: UUID,
        actor_user_id: UUID | None,
        reason: str | None,
    ) -> None:
        """Persist an append-only status-change record when the item actually transitions."""
        if self.status_history_repository is None:
            return

        await self.status_history_repository.record(
            organization_id=organization_id,
            work_item_id=work_item.id,
            previous_status=previous_status,
            new_status=new_status,
            actor_user_id=actor_user_id,
            reason=reason,
        )

    async def update_work_item_status(
        self,
        *,
        work_item_id: UUID,
        new_status: str,
        organization_id: UUID,
        actor_user_id: UUID | None,
        reason: str | None = None,
    ) -> WorkItemModel:
        """Update the status of a work item with validation.

        Args:
            work_item_id: Work item ID
            new_status: New status value
            organization_id: Organization ID
            actor_user_id: User performing the update

        Returns:
            The updated work item

        Raises:
            NotFoundError: If work item not found
            UnprocessableEntityError: If status transition is invalid
        """
        # Fetch the work item
        work_item = await self.repository.get_in_organization(
            work_item_id=work_item_id,
            organization_id=organization_id,
        )
        if work_item is None:
            raise NotFoundError(f"Work item '{work_item_id}' not found")

        # Parse new status
        try:
            new_status_enum = WorkStatus(new_status)
        except ValueError as error:
            valid_statuses = ", ".join(s.value for s in WorkStatus)
            raise UnprocessableEntityError(
                f"Invalid status '{new_status}'. Valid statuses: {valid_statuses}"
            ) from error

        # Validate transition
        try:
            WorkItemStateTransition.validate_transition(work_item.status, new_status_enum)
        except InvalidTransitionError as e:
            raise UnprocessableEntityError(str(e)) from e

        # Apply transition if it's a real change
        old_status = work_item.status
        if old_status != new_status_enum:
            work_item.status = new_status_enum
            await self.repository.session.flush()

            await self._record_status_history(
                work_item=work_item,
                previous_status=old_status,
                new_status=new_status_enum,
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                reason=reason,
            )

            await self._audit(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=AuditAction.UPDATE,
                resource_id=work_item.id,
                metadata={
                    "field": "status",
                    "old_value": old_status.value,
                    "new_value": new_status_enum.value,
                },
            )

        return work_item

    async def get_work_item(
        self,
        *,
        work_item_id: UUID,
        organization_id: UUID,
    ) -> WorkItemModel:
        """Get a work item by ID within organization scope.

        Args:
            work_item_id: Work item ID
            organization_id: Organization ID

        Returns:
            The work item if found and scoped correctly

        Raises:
            NotFoundError: If work item not found
        """
        work_item = await self.repository.get_in_organization(
            work_item_id=work_item_id,
            organization_id=organization_id,
        )
        if work_item is None:
            raise NotFoundError(f"Work item '{work_item_id}' not found")
        return work_item

    async def list_work_items(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        department_id: UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
        overdue: bool | None = None,
    ) -> tuple[list[WorkItemModel], int]:
        """List work items in a project within organization scope."""
        await self._get_project(project_id=project_id, organization_id=organization_id)

        priority_value: str | None = None
        if priority is not None:
            try:
                priority_value = WorkPriority(priority).value
            except ValueError as error:
                valid_priorities = ", ".join(item.value for item in WorkPriority)
                raise UnprocessableEntityError(
                    f"Invalid priority '{priority}'. Valid priorities: {valid_priorities}"
                ) from error

        return await self.repository.list_in_project(
            project_id=project_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            department_id=department_id,
            status=status,
            priority=priority_value,
            overdue=overdue,
        )


__all__ = ["WorkItemService"]
