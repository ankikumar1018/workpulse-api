"""add message delivery status history"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c9b2d7f4e1a0"
down_revision: str | Sequence[str] | None = "b5d4a0bfc0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE delivery_status ADD VALUE IF NOT EXISTS 'processing'")
    op.execute("ALTER TYPE delivery_status ADD VALUE IF NOT EXISTS 'cancelled'")
    delivery_status = postgresql.ENUM(
        "queued",
        "sent",
        "delivered",
        "failed",
        "processing",
        "cancelled",
        name="delivery_status",
        create_type=False,
    )
    op.create_table(
        "message_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", delivery_status, nullable=True),
        sa.Column("new_status", delivery_status, nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "message_id"],
            ["messages.organization_id", "messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_message_status_history_message_id_created_at",
        "message_status_history",
        ["message_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_message_status_history_message_id_created_at",
        table_name="message_status_history",
    )
    op.drop_table("message_status_history")
