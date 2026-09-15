"""Unit tests for the WhatsApp Business Cloud API adapter."""

import json
from uuid import uuid4

import httpx
import pytest

from app.domain.enums import Channel
from app.domain.message import Message
from app.domain.message_provider import MessageProviderConfigurationError, MessageProviderError
from app.infrastructure.providers.whatsapp import WhatsAppCloudProvider


def make_message(channel: Channel = Channel.WHATSAPP) -> Message:
    """Build a rendered outbound message for provider tests."""
    return Message(
        id=uuid4(),
        organization_id=uuid4(),
        worker_id=uuid4(),
        channel=channel,
        recipient_phone_number="+15551234567",
        rendered_body="Kitchen cabinets are ready for review.",
        dispatch_key="project-1:daily-status:worker-1",
    )


@pytest.mark.asyncio
async def test_whatsapp_provider_submits_text_and_returns_provider_identity() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.123"}]})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(respond)
    )
    provider = WhatsAppCloudProvider(
        access_token="test-token",
        phone_number_id="phone-123",
        api_version="v24.0",
        client=client,
    )

    result = await provider.send(make_message())

    assert result.provider_name == "whatsapp_cloud"
    assert result.provider_message_id == "wamid.123"
    assert requests[0].url == httpx.URL("https://graph.facebook.com/v24.0/phone-123/messages")
    assert requests[0].headers["Authorization"] == "Bearer test-token"
    assert json.loads(requests[0].content) == {
        "messaging_product": "whatsapp",
        "to": "15551234567",
        "type": "text",
        "text": {"body": "Kitchen cabinets are ready for review."},
    }
    await client.aclose()


@pytest.mark.asyncio
async def test_whatsapp_provider_requires_credentials() -> None:
    provider = WhatsAppCloudProvider(
        access_token=None,
        phone_number_id=None,
        api_version="v24.0",
    )

    with pytest.raises(MessageProviderConfigurationError, match="must be configured"):
        await provider.send(make_message())


@pytest.mark.asyncio
async def test_whatsapp_provider_normalizes_provider_errors() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(401, json={"error": {}}))
    )
    provider = WhatsAppCloudProvider(
        access_token="test-token",
        phone_number_id="phone-123",
        api_version="v24.0",
        client=client,
    )

    with pytest.raises(MessageProviderError, match="status 401"):
        await provider.send(make_message())
    await client.aclose()
