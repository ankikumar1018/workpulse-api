"""Organization model."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import OrganizationStatus, SubscriptionStatus
from core.database import Base, TimestampMixin


def enum_values(enum_type: type[enum.StrEnum]) -> tuple[str, ...]:
    """Persist enum values rather than Python member names."""
    return tuple(member.value for member in enum_type)


class Organization(TimestampMixin, Base):
    """Top-level tenant boundary."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(
            OrganizationStatus,
            name="organization_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=OrganizationStatus.INACTIVE,
        server_default=OrganizationStatus.INACTIVE.value,
    )
    subscription_status: Mapped[SubscriptionStatus | None] = mapped_column(
        Enum(
            SubscriptionStatus,
            name="subscription_status",
            values_callable=enum_values,
        ),
    )


__all__ = ["Organization"]
