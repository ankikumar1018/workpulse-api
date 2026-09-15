"""Deterministic identities for communication jobs and outbound messages."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID


def _canonical_key_payload(
    *,
    organization_id: UUID,
    schedule_id: UUID,
    template_id: UUID,
    worker_id: UUID,
    execution_at: datetime,
) -> str:
    """Serialize logical execution inputs in a stable, timezone-aware form."""
    if execution_at.tzinfo is None:
        raise ValueError("execution_at must include timezone information")
    payload = {
        "organization_id": str(organization_id),
        "schedule_id": str(schedule_id),
        "template_id": str(template_id),
        "worker_id": str(worker_id),
        "execution_at": execution_at.isoformat(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _build_key(prefix: str, payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def build_message_dispatch_key(
    *,
    organization_id: UUID,
    schedule_id: UUID,
    template_id: UUID,
    worker_id: UUID,
    execution_at: datetime,
) -> str:
    """Build the stable database identity for one logical message execution."""
    return _build_key(
        "msg",
        _canonical_key_payload(
            organization_id=organization_id,
            schedule_id=schedule_id,
            template_id=template_id,
            worker_id=worker_id,
            execution_at=execution_at,
        ),
    )


def build_communication_job_key(
    *,
    organization_id: UUID,
    schedule_id: UUID,
    template_id: UUID,
    worker_id: UUID,
    execution_at: datetime,
) -> str:
    """Build the stable identity for a future queue-independent job record."""
    return _build_key(
        "job",
        _canonical_key_payload(
            organization_id=organization_id,
            schedule_id=schedule_id,
            template_id=template_id,
            worker_id=worker_id,
            execution_at=execution_at,
        ),
    )


__all__ = ["build_communication_job_key", "build_message_dispatch_key"]
