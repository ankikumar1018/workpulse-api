"""add work item status history

Revision ID: b5d4a0bfc0d1
Revises: b7d4f65a90aa
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b5d4a0bfc0d1"
down_revision: str | Sequence[str] | None = "b7d4f65a90aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_item_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "previous_status",
            sa.Enum("open", "in_progress", "blocked", "done", "cancelled", name="work_status"),
            nullable=False,
        ),
        sa.Column(
            "new_status",
            sa.Enum("open", "in_progress", "blocked", "done", "cancelled", name="work_status"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["work_item_id"],
            ["work_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_work_item_status_history_work_item_id_created_at",
        "work_item_status_history",
        ["work_item_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_work_item_status_history_work_item_id_created_at", "work_item_status_history")
    op.drop_table("work_item_status_history")
