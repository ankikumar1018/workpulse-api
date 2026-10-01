"""add queue-independent communication jobs

Revision ID: g7h8i9j0k1l2
Revises: a1e6f5b9c321, f4c3a1b29d77
Create Date: 2026-10-01 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "g7h8i9j0k1l2"
down_revision = ("a1e6f5b9c321", "f4c3a1b29d77")
branch_labels = None
depends_on = None


def upgrade() -> None:
    communication_job_status = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        "cancelled",
        "suppressed",
        name="communication_job_status",
        create_type=False,
    )
    communication_job_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "communication_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=True),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=True),
        sa.Column("worker_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            postgresql.ENUM("whatsapp", name="channel_type", create_type=False),
            nullable=False,
        ),
        sa.Column("execution_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_key", sa.String(length=128), nullable=False),
        sa.Column("status", communication_job_status, nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="ck_communication_jobs_attempt_count_gte_zero"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "schedule_id"],
            ["schedules.organization_id", "schedules.id"],
            ondelete="SET NULL (schedule_id)",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "template_id"],
            ["templates.organization_id", "templates.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "work_item_id"],
            ["work_items.organization_id", "work_items.id"],
            ondelete="SET NULL (work_item_id)",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "worker_id"],
            ["workers.organization_id", "workers.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_communication_jobs_org_id"),
        sa.UniqueConstraint("organization_id", "job_key", name="uq_communication_jobs_org_job_key"),
    )
    op.create_table(
        "communication_job_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column(
            "previous_status",
            postgresql.ENUM(name="communication_job_status", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            postgresql.ENUM(name="communication_job_status", create_type=False),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("queue_reference", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "job_id"],
            ["communication_jobs.organization_id", "communication_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("communication_job_status_history")
    op.drop_table("communication_jobs")
    sa.Enum(name="communication_job_status").drop(op.get_bind(), checkfirst=True)
