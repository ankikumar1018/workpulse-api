"""Contracts for provider-specific outbound message adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class MessageProviderError(Exception):
    """Raised when a message provider rejects or cannot accept a message."""

    def __init__(
        self, message: str, *, error_code: str = "PROVIDER_ERROR", retryable: bool = False
    ):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable


class MessageProviderConfigurationError(MessageProviderError):
    """Raised when a message provider is not configured for use."""

    def __init__(self, message: str):
        super().__init__(message, error_code="PROVIDER_CONFIGURATION_ERROR")


@dataclass(frozen=True)
class ProviderTemplate:
    """Approved provider template with positional body parameters."""

    name: str
    language: str
    body_parameters: tuple[str, ...]


@dataclass(frozen=True)
class TemplateOutboundMessage:
    """Provider-neutral outbound data including an approved template."""

    channel: object
    recipient_phone_number: str
    rendered_body: str
    provider_template: ProviderTemplate


@dataclass(frozen=True)
class ProviderSendResult:
    """Provider-independent outcome of accepting an outbound message."""

    provider_name: str
    provider_message_id: str


class OutboundMessage(Protocol):
    """Data required by an outbound channel provider."""

    @property
    def channel(self) -> object: ...

    @property
    def recipient_phone_number(self) -> str: ...

    @property
    def rendered_body(self) -> str: ...


class OutboundMessageProvider(Protocol):
    """Send a rendered message through a channel-specific external provider."""

    async def send(self, message: OutboundMessage) -> ProviderSendResult:
        """Submit a message and return its external provider identity."""


__all__ = [
    "MessageProviderConfigurationError",
    "MessageProviderError",
    "OutboundMessage",
    "OutboundMessageProvider",
    "ProviderSendResult",
]
