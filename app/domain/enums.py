"""Business enums shared across application layers."""

from __future__ import annotations

import enum


class EntityStatus(enum.StrEnum):
    """Common active/archive lifecycle state."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class OrganizationStatus(enum.StrEnum):
    """Organization lifecycle state."""

    PROVISIONING = "provisioning"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class SubscriptionStatus(enum.StrEnum):
    """Organization subscription lifecycle state."""

    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class WorkerStatus(enum.StrEnum):
    """Worker lifecycle state."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class ConsentStatus(enum.StrEnum):
    """Worker communication consent state for outbound channels."""

    OPTED_IN = "opted_in"
    OPTED_OUT = "opted_out"


class WorkPriority(enum.StrEnum):
    """Work item urgency level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkStatus(enum.StrEnum):
    """Work item current state."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class Channel(enum.StrEnum):
    """Supported outbound channels for MVP."""

    WHATSAPP = "whatsapp"


class ScheduleStatus(enum.StrEnum):
    """Schedule state."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DeliveryStatus(enum.StrEnum):
    """Message delivery progress."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class AuditAction(enum.StrEnum):
    """Minimal audit action set for phase 1."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEND = "send"


__all__ = [
    "AuditAction",
    "Channel",
    "ConsentStatus",
    "DeliveryStatus",
    "EntityStatus",
    "OrganizationStatus",
    "ScheduleStatus",
    "SubscriptionStatus",
    "WorkPriority",
    "WorkStatus",
    "WorkerStatus",
]
