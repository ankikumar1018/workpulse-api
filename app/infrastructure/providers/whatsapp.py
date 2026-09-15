"""WhatsApp Business Cloud API outbound-message adapter."""

from __future__ import annotations

import httpx

from app.domain.enums import Channel
from app.domain.message import Message
from app.domain.message_provider import (
    MessageProviderConfigurationError,
    MessageProviderError,
    ProviderSendResult,
)


class WhatsAppCloudProvider:
    """Submit rendered WhatsApp text messages through Meta's Cloud API."""

    provider_name = "whatsapp_cloud"
    api_base_url = "https://graph.facebook.com"

    def __init__(
        self,
        *,
        access_token: str | None,
        phone_number_id: str | None,
        api_version: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._api_version = api_version
        self._client = client

    async def send(self, message: Message) -> ProviderSendResult:
        """Send a rendered text message and return Meta's message identifier."""
        if message.channel != Channel.WHATSAPP:
            raise MessageProviderError("WhatsApp provider can only send WhatsApp messages.")
        if not self._access_token or not self._phone_number_id:
            raise MessageProviderConfigurationError(
                "WhatsApp access token and phone number ID must be configured."
            )

        response = await self._post_messages(message)
        if response.is_error:
            raise MessageProviderError(
                f"WhatsApp Cloud API rejected the message with status {response.status_code}.",
                error_code=f"WHATSAPP_HTTP_{response.status_code}",
                retryable=response.status_code == 429 or response.status_code >= 500,
            )

        provider_message_id = self._extract_message_id(response)
        return ProviderSendResult(
            provider_name=self.provider_name,
            provider_message_id=provider_message_id,
        )

    async def send_template(
        self,
        *,
        recipient_phone_number: str,
        template_name: str,
        language: str,
        body_parameters: list[str],
    ) -> ProviderSendResult:
        """Send an approved Meta template without making it a domain identifier."""
        if not self._access_token or not self._phone_number_id:
            raise MessageProviderConfigurationError(
                "WhatsApp access token and phone number ID must be configured."
            )
        response = await self._post_payload(
            {
                "messaging_product": "whatsapp",
                "to": recipient_phone_number.removeprefix("+"),
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": value} for value in body_parameters],
                        }
                    ],
                },
            }
        )
        if response.is_error:
            raise MessageProviderError(
                f"WhatsApp Cloud API rejected the template with status {response.status_code}.",
                error_code=f"WHATSAPP_HTTP_{response.status_code}",
                retryable=response.status_code == 429 or response.status_code >= 500,
            )
        return ProviderSendResult(self.provider_name, self._extract_message_id(response))

    async def _post_messages(self, message: Message) -> httpx.Response:
        return await self._post_payload(
            {
                "messaging_product": "whatsapp",
                "to": message.recipient_phone_number.removeprefix("+"),
                "type": "text",
                "text": {"body": message.rendered_body},
            }
        )

    async def _post_payload(self, payload: dict[str, object]) -> httpx.Response:
        client = self._client
        close_client = client is None
        if client is None:
            client = httpx.AsyncClient()

        try:
            return await client.post(
                f"{self.api_base_url}/{self._api_version}/{self._phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self._access_token}"},
                json=payload,
            )
        except httpx.HTTPError as error:
            raise MessageProviderError(
                "WhatsApp Cloud API request failed.",
                error_code="WHATSAPP_NETWORK_ERROR",
                retryable=True,
            ) from error
        finally:
            if close_client:
                await client.aclose()

    @staticmethod
    def _extract_message_id(response: httpx.Response) -> str:
        try:
            messages = response.json()["messages"]
            provider_message_id = messages[0]["id"]
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise MessageProviderError(
                "WhatsApp Cloud API response did not include a message identifier."
            ) from error
        if not isinstance(provider_message_id, str) or not provider_message_id:
            raise MessageProviderError(
                "WhatsApp Cloud API response included an invalid message identifier."
            )
        return provider_message_id
