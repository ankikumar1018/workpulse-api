"""Worker request schemas."""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ContactChannel = Literal["whatsapp"]
WorkerConsentStatus = Literal["opted_in", "opted_out"]
WorkerStatus = Literal["active", "inactive"]


def normalize_phone_number(value: str) -> str:
    """Normalize user phone input to strict E.164 form."""

    compact = re.sub(r"[\s().-]", "", value.strip())
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"
    if not compact.startswith("+") and compact.isdigit():
        compact = f"+{compact}"
    if not re.fullmatch(r"^\+[1-9][0-9]{1,14}$", compact):
        raise ValueError("phone_number must be a valid E.164 number")
    return compact


class WorkerCreateRequest(BaseModel):
    """Create a worker in a department."""

    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(max_length=16)
    contact_channel: ContactChannel = "whatsapp"
    consent_status: WorkerConsentStatus = "opted_in"

    @field_validator("phone_number", mode="before")
    @classmethod
    def normalize_phone_number(cls, value: str) -> str:
        return normalize_phone_number(value)


class WorkerUpdateRequest(BaseModel):
    """Partially update a worker."""

    department_id: UUID | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone_number: str | None = Field(None, max_length=16)
    contact_channel: ContactChannel | None = None
    consent_status: WorkerConsentStatus | None = None
    status: WorkerStatus | None = None

    @field_validator("phone_number", mode="before")
    @classmethod
    def normalize_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_phone_number(value)


__all__ = [
    "ContactChannel",
    "WorkerConsentStatus",
    "WorkerCreateRequest",
    "WorkerStatus",
    "WorkerUpdateRequest",
]
