"""Phase 1 relational schema models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import (
    AuditAction,
    Channel,
    DeliveryStatus,
    EntityStatus,
    OrganizationStatus,
    ScheduleStatus,
    SubscriptionStatus,
    WorkerStatus,
    WorkPriority,
    WorkStatus,
)
from app.infrastructure.db.base import Base, TimestampMixin


def enum_values(enum_type: type[enum.StrEnum]) -> tuple[str, ...]:
    """Persist enum values rather than Python member names."""

    return tuple(member.value for member in enum_type)


class Organization(TimestampMixin, Base):
    """Top-level tenant boundary."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(OrganizationStatus, name="organization_status", values_callable=enum_values),
        nullable=False,
        default=OrganizationStatus.INACTIVE,
        server_default=OrganizationStatus.INACTIVE.value,
    )
    subscription_status: Mapped[SubscriptionStatus | None] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", values_callable=enum_values),
    )


class User(TimestampMixin, Base):
    """Administrator identity scoped to an organization."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")


class RefreshSession(Base):
    """Rotatable and revocable refresh-token session."""

    __tablename__ = "refresh_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Project(TimestampMixin, Base):
    """Project container scoped to an organization."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_projects_end_date_gte_start_date",
        ),
        UniqueConstraint("organization_id", "name", name="uq_projects_org_name"),
        UniqueConstraint("organization_id", "id", name="uq_projects_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus, name="entity_status", values_callable=enum_values),
        nullable=False,
        default=EntityStatus.ACTIVE,
        server_default=EntityStatus.ACTIVE.value,
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class Department(TimestampMixin, Base):
    """Department within a project."""

    __tablename__ = "departments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("project_id", "name", name="uq_departments_project_name"),
        UniqueConstraint("organization_id", "id", name="uq_departments_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus, name="entity_status", values_callable=enum_values),
        nullable=False,
        default=EntityStatus.ACTIVE,
        server_default=EntityStatus.ACTIVE.value,
    )


class Worker(TimestampMixin, Base):
    """Worker record for tasking and communication."""

    __tablename__ = "workers"
    __table_args__ = (
        CheckConstraint(
            "phone_number ~ '^\\+[1-9][0-9]{1,14}$'",
            name="ck_workers_phone_number_format",
        ),
        UniqueConstraint("organization_id", "phone_number", name="uq_workers_org_phone"),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_workers_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status", values_callable=enum_values),
        nullable=False,
        default=WorkerStatus.ACTIVE,
        server_default=WorkerStatus.ACTIVE.value,
    )


class WorkItem(TimestampMixin, Base):
    """Operational work tracked within a project and department."""

    __tablename__ = "work_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "worker_id"],
            ["workers.organization_id", "workers.id"],
            ondelete="SET NULL",
        ),
        UniqueConstraint("organization_id", "id", name="uq_work_items_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[WorkPriority] = mapped_column(
        Enum(WorkPriority, name="work_priority", values_callable=enum_values),
        nullable=False,
        default=WorkPriority.MEDIUM,
        server_default=WorkPriority.MEDIUM.value,
    )
    status: Mapped[WorkStatus] = mapped_column(
        Enum(WorkStatus, name="work_status", values_callable=enum_values),
        nullable=False,
        default=WorkStatus.OPEN,
        server_default=WorkStatus.OPEN.value,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class Template(TimestampMixin, Base):
    """Message template configuration."""

    __tablename__ = "templates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("project_id", "name", "channel", name="uq_templates_project_name_channel"),
        UniqueConstraint("organization_id", "id", name="uq_templates_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[Channel] = mapped_column(
        Enum(Channel, name="channel_type", values_callable=enum_values),
        nullable=False,
        default=Channel.WHATSAPP,
        server_default=Channel.WHATSAPP.value,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variable_schema_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus, name="entity_status", values_callable=enum_values),
        nullable=False,
        default=EntityStatus.ACTIVE,
        server_default=EntityStatus.ACTIVE.value,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class Schedule(TimestampMixin, Base):
    """Schedule that controls outbound communication cadence."""

    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("interval_seconds > 0", name="ck_schedules_interval_seconds_gt_zero"),
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "template_id"],
            ["templates.organization_id", "templates.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_schedules_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    window_start_local: Mapped[time] = mapped_column(Time, nullable=False)
    window_end_local: Mapped[time] = mapped_column(Time, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus, name="schedule_status", values_callable=enum_values),
        nullable=False,
        default=ScheduleStatus.PAUSED,
        server_default=ScheduleStatus.PAUSED.value,
    )
    next_run_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(TimestampMixin, Base):
    """Outbound message and latest delivery state."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("organization_id", "dispatch_key", name="uq_messages_org_dispatch_key"),
        UniqueConstraint(
            "provider_name", "provider_message_id", name="uq_messages_provider_message_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "schedule_id"],
            ["schedules.organization_id", "schedules.id"],
            ondelete="SET NULL (schedule_id)",
        ),
        ForeignKeyConstraint(
            ["organization_id", "work_item_id"],
            ["work_items.organization_id", "work_items.id"],
            ondelete="SET NULL (work_item_id)",
        ),
        ForeignKeyConstraint(
            ["organization_id", "worker_id"],
            ["workers.organization_id", "workers.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_messages_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
    )
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    channel: Mapped[Channel] = mapped_column(
        Enum(Channel, name="channel_type", values_callable=enum_values),
        nullable=False,
        default=Channel.WHATSAPP,
        server_default=Channel.WHATSAPP.value,
    )
    recipient_phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    rendered_body: Mapped[str] = mapped_column(Text, nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(100))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    dispatch_key: Mapped[str] = mapped_column(String(128), nullable=False)
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status", values_callable=enum_values),
        nullable=False,
        default=DeliveryStatus.QUEUED,
        server_default=DeliveryStatus.QUEUED.value,
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    """Immutable audit trail for phase 1 actions."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", values_callable=enum_values),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
