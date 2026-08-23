"""add worker contact consent fields

Revision ID: b7d4f65a90aa
Revises: f4c3a1b29d77
Create Date: 2026-08-23 18:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7d4f65a90aa"
down_revision: str | Sequence[str] | None = "f4c3a1b29d77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    consent_enum = sa.Enum("opted_in", "opted_out", name="consent_status")
    consent_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "workers",
        sa.Column(
            "contact_channel",
            sa.Enum("whatsapp", name="channel_type", create_type=False),
            nullable=False,
            server_default="whatsapp",
        ),
    )
    op.add_column(
        "workers",
        sa.Column(
            "consent_status",
            sa.Enum("opted_in", "opted_out", name="consent_status"),
            nullable=False,
            server_default="opted_in",
        ),
    )


def downgrade() -> None:
    op.drop_column("workers", "consent_status")
    op.drop_column("workers", "contact_channel")

    consent_enum = sa.Enum("opted_in", "opted_out", name="consent_status")
    consent_enum.drop(op.get_bind(), checkfirst=True)
