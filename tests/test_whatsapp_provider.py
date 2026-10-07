"""Unit tests for the WhatsApp Business Cloud API adapter."""

import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.domain.enums import Channel
from app.domain.message import Message
from app.domain.message_provider import (
    MessageProviderConfigurationError,
    MessageProviderError,
    ProviderTemplate,
    TemplateOutboundMessage,
)
from app.infrastructure.providers.whatsapp import WhatsAppCloudProvider
from app.workers import whatsapp_smoke


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


def test_smoke_check_does_not_send_or_expose_secrets(monkeypatch, capsys):
    for name in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
    ):
        monkeypatch.setattr(whatsapp_smoke.settings, name, "private-test-value")

    async def forbidden_send(_args):
        pytest.fail("Configuration check must not send a message")

    monkeypatch.setattr(whatsapp_smoke, "send_template", forbidden_send)

    assert whatsapp_smoke.main([]) == 0
    output = capsys.readouterr().out
    assert "private-test-value" not in output
    assert "no network request" in output


@pytest.mark.parametrize(
    "arguments",
    [
        ["--send"],
        ["--send", "--recipient", "+15551234567"],
        ["--send", "--recipient", "invalid", "--confirm-opt-in"],
    ],
)
def test_smoke_send_requires_explicit_recipient_and_consent(arguments):
    with pytest.raises(SystemExit) as exception_info:
        whatsapp_smoke.main(arguments)
    assert exception_info.value.code == 2


def test_smoke_check_reports_missing_settings_without_sending(monkeypatch, capsys):
    monkeypatch.setattr(whatsapp_smoke.settings, "WHATSAPP_ACCESS_TOKEN", None)
    assert whatsapp_smoke.main([]) == 1
    assert "WHATSAPP_ACCESS_TOKEN: missing" in capsys.readouterr().out


@pytest.mark.parametrize(
    "scenario, exit_code, outcome",
    [
        ("success", 0, "wamid.local-test"),
        ("transient", 1, "WHATSAPP_HTTP_429"),
        ("permanent", 1, "WHATSAPP_HTTP_400"),
    ],
)
def test_local_smoke_uses_mock_transport_without_credentials(
    monkeypatch, capsys, scenario, exit_code, outcome
):
    for name in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
    ):
        monkeypatch.setattr(whatsapp_smoke.settings, name, None)

    async def reject_network(*_args, **_kwargs):
        pytest.fail("Local testing must never use a network transport")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject_network)

    result = whatsapp_smoke.main(["--local", "--scenario", scenario])

    assert result == exit_code
    output = capsys.readouterr().out
    assert "LOCAL SIMULATION" in output
    assert "type=template, template=hello_world" in output
    assert outcome in output


@pytest.mark.parametrize(
    "arguments",
    [
        ["--local", "--send"],
        ["--scenario", "transient"],
    ],
)
def test_local_and_live_smoke_modes_cannot_be_mixed(arguments):
    with pytest.raises(SystemExit) as exception_info:
        whatsapp_smoke.main(arguments)
    assert exception_info.value.code == 2


@pytest.mark.asyncio
async def test_whatsapp_provider_submits_text_and_returns_provider_identity() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.123"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
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
@pytest.mark.parametrize("parameters", [(), ("Ada", "Apollo")])
async def test_whatsapp_send_uses_approved_template(parameters):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.template"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        provider = WhatsAppCloudProvider(
            access_token="test-token",
            phone_number_id="phone-123",
            api_version="v24.0",
            client=client,
        )
        outbound = TemplateOutboundMessage(
            channel=Channel.WHATSAPP,
            recipient_phone_number="+15551234567",
            rendered_body="Local preview",
            provider_template=ProviderTemplate("work_update", "en_US", parameters),
        )

        result = await provider.send(outbound)

    payload = json.loads(requests[0].content)
    assert result.provider_message_id == "wamid.template"
    assert payload["type"] == "template"
    assert payload["template"]["name"] == "work_update"
    assert payload["template"]["language"] == {"code": "en_US"}
    assert payload["template"]["components"] == (
        [{"type": "body", "parameters": [{"type": "text", "text": value} for value in parameters]}]
        if parameters
        else []
    )
    assert "text" not in payload


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


@pytest.mark.asyncio
async def test_whatsapp_provider_classifies_transient_http_failures() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(429, json={"error": {}}))
    )
    provider = WhatsAppCloudProvider(
        access_token="test-token",
        phone_number_id="phone-123",
        api_version="v24.0",
        client=client,
    )

    with pytest.raises(MessageProviderError) as exception_info:
        await provider.send(make_message())

    assert exception_info.value.error_code == "WHATSAPP_HTTP_429"
    assert exception_info.value.retryable is True
    await client.aclose()


@pytest.mark.asyncio
async def test_whatsapp_provider_rejects_malformed_success_payload() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"messages": []}))
    )
    provider = WhatsAppCloudProvider(
        access_token="test-token",
        phone_number_id="phone-123",
        api_version="v24.0",
        client=client,
    )

    with pytest.raises(MessageProviderError, match="did not include a message identifier"):
        await provider.send(make_message())
    await client.aclose()


@pytest.mark.asyncio
async def test_whatsapp_provider_rejects_wrong_channel() -> None:
    provider = WhatsAppCloudProvider(
        access_token="test-token",
        phone_number_id="phone-123",
        api_version="v24.0",
    )

    wrong_channel_message = SimpleNamespace(
        channel="sms",
        recipient_phone_number="+15551234567",
        rendered_body="Work update",
    )

    with pytest.raises(MessageProviderError, match="only send WhatsApp messages"):
        await provider.send(wrong_channel_message)
