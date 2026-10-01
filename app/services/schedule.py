"""Schedule configuration and lifecycle business logic."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.errors import NotFoundError, UnprocessableEntityError
from app.domain.enums import AuditAction, EntityStatus, ScheduleStatus
from app.domain.scheduling import calculate_next_execution_at_utc
from app.infrastructure.db.models import Department, Project, Schedule, Template
from app.repositories.audit import AuditRepository
from app.repositories.schedule import ScheduleRepository


class ScheduleService:
    """Manage schedules within active tenant-owned project configuration."""

    def __init__(
        self,
        repository: ScheduleRepository,
        audit_repository: AuditRepository | None = None,
    ):
        self.repository = repository
        self.audit_repository = audit_repository

    async def _validate_scope(
        self,
        *,
        project_id: UUID,
        department_id: UUID,
        template_id: UUID,
        organization_id: UUID,
    ) -> tuple[Project, Department, Template]:
        session = self.repository.session
        project = await session.get(Project, project_id)
        if project is None or project.organization_id != organization_id:
            raise NotFoundError(f"Project '{project_id}' not found")
        department = await session.get(Department, department_id)
        if department is None or department.organization_id != organization_id:
            raise NotFoundError(f"Department '{department_id}' not found")
        template = await session.get(Template, template_id)
        if template is None or template.organization_id != organization_id:
            raise NotFoundError(f"Template '{template_id}' not found")
        if department.project_id != project_id:
            raise UnprocessableEntityError("Department must belong to the selected project")
        if template.project_id != project_id:
            raise UnprocessableEntityError("Template must belong to the selected project")
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived projects cannot have active schedules")
        if department.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived departments cannot have active schedules")
        if template.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived templates cannot be scheduled")
        return project, department, template

    @staticmethod
    def _validate_configuration(
        *,
        timezone: str,
        window_start_local: time,
        window_end_local: time,
        interval_seconds: int,
    ) -> None:
        try:
            ZoneInfo(timezone)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise UnprocessableEntityError(f"Unknown timezone '{timezone}'") from error
        if window_start_local >= window_end_local:
            raise UnprocessableEntityError("Schedule end time must be later than start time")
        if interval_seconds <= 0:
            raise UnprocessableEntityError("Schedule interval must be greater than zero")

    async def create_schedule(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        department_id: UUID,
        template_id: UUID,
        timezone: str,
        window_start_local: time,
        window_end_local: time,
        interval_seconds: int,
    ) -> Schedule:
        self._validate_configuration(
            timezone=timezone,
            window_start_local=window_start_local,
            window_end_local=window_end_local,
            interval_seconds=interval_seconds,
        )
        await self._validate_scope(
            project_id=project_id,
            department_id=department_id,
            template_id=template_id,
            organization_id=organization_id,
        )
        schedule = await self.repository.create(
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "department_id": department_id,
                "template_id": template_id,
                "timezone": timezone,
                "window_start_local": window_start_local,
                "window_end_local": window_end_local,
                "interval_seconds": interval_seconds,
                "status": ScheduleStatus.PAUSED,
            }
        )
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.CREATE,
            schedule=schedule,
            metadata={"project_id": str(project_id), "template_id": str(template_id)},
        )
        return schedule

    async def get_schedule(self, *, schedule_id: UUID, organization_id: UUID) -> Schedule:
        schedule = await self.repository.get_in_organization(
            schedule_id=schedule_id,
            organization_id=organization_id,
        )
        if schedule is None:
            raise NotFoundError(f"Schedule '{schedule_id}' not found")
        return schedule

    async def list_schedules(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Schedule], int]:
        project = await self.repository.session.get(Project, project_id)
        if project is None or project.organization_id != organization_id:
            raise NotFoundError(f"Project '{project_id}' not found")
        return await self.repository.list_in_project(
            project_id=project_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    async def update_schedule(
        self,
        *,
        schedule_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        update_data: dict[str, Any],
    ) -> Schedule:
        schedule = await self.get_schedule(schedule_id=schedule_id, organization_id=organization_id)
        if schedule.status == ScheduleStatus.ACTIVE:
            raise UnprocessableEntityError("Pause a schedule before changing its configuration")
        if any(value is None for value in update_data.values()):
            raise UnprocessableEntityError("Schedule configuration values cannot be null")
        values = {
            "timezone": update_data.get("timezone", schedule.timezone),
            "window_start_local": update_data.get(
                "window_start_local", schedule.window_start_local
            ),
            "window_end_local": update_data.get("window_end_local", schedule.window_end_local),
            "interval_seconds": update_data.get("interval_seconds", schedule.interval_seconds),
        }
        self._validate_configuration(**values)
        scope = {
            "project_id": schedule.project_id,
            "department_id": update_data.get("department_id", schedule.department_id),
            "template_id": update_data.get("template_id", schedule.template_id),
            "organization_id": organization_id,
        }
        await self._validate_scope(**scope)
        updated = await self.repository.update(schedule_id, update_data)
        if updated is None:
            raise NotFoundError(f"Schedule '{schedule_id}' not found")
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            schedule=updated,
            metadata=dict(update_data),
        )
        return updated

    async def set_schedule_status(
        self,
        *,
        schedule_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        status: ScheduleStatus,
    ) -> Schedule:
        schedule = await self.get_schedule(schedule_id=schedule_id, organization_id=organization_id)
        if status == ScheduleStatus.ACTIVE:
            await self._validate_scope(
                project_id=schedule.project_id,
                department_id=schedule.department_id,
                template_id=schedule.template_id,
                organization_id=organization_id,
            )
            schedule.next_run_at_utc = calculate_next_execution_at_utc(
                reference_at=datetime.now(UTC),
                timezone=schedule.timezone,
                window_start_local=schedule.window_start_local,
                window_end_local=schedule.window_end_local,
                interval_seconds=schedule.interval_seconds,
            )
        schedule.status = status
        if status == ScheduleStatus.PAUSED:
            schedule.next_run_at_utc = None
        await self.repository.session.commit()
        await self.repository.session.refresh(schedule)
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            schedule=schedule,
            metadata={"status": status.value},
        )
        return schedule

    async def _audit(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        action: AuditAction,
        schedule: Schedule,
        metadata: dict[str, Any],
    ) -> None:
        if self.audit_repository is not None:
            await self.audit_repository.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type="schedule",
                resource_id=schedule.id,
                metadata=metadata,
            )


__all__ = ["ScheduleService"]
