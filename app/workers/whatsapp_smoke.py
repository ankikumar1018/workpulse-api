"""Explicit, single-recipient WhatsApp connectivity check; no database writes."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections.abc import Sequence

import httpx

from app.domain.message_provider import MessageProviderError
from app.infrastructure.providers.whatsapp import WhatsAppCloudProvider
from core.config import settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--send", action="store_true", help="Send exactly one approved template")
    mode.add_argument(
        "--local", action="store_true", help="Exercise the real adapter with an offline HTTP mock"
    )
    parser.add_argument(
        "--scenario",
        choices=("success", "transient", "permanent"),
        default="success",
        help="Local mock response scenario",
    )
    parser.add_argument("--recipient", help="Opted-in recipient in E.164 format, including +")
    parser.add_argument("--confirm-opt-in", action="store_true", help="Confirm recipient consent")
    parser.add_argument(
        "--template", default="hello_world", help="Exact approved Meta template name"
    )
    parser.add_argument("--language", default="en_US", help="Exact approved template language code")
    parser.add_argument(
        "--parameter",
        action="append",
        default=[],
        help="Body parameter, in positional order; repeat as needed",
    )
    return parser


async def send_template(args: argparse.Namespace) -> str:
    def local_response(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        print(
            f"Local request: type={payload['type']}, template={payload['template']['name']}, language={payload['template']['language']['code']}"
        )
        if args.scenario == "transient":
            return httpx.Response(429, json={"error": {"code": 130429}})
        if args.scenario == "permanent":
            return httpx.Response(400, json={"error": {"code": 132001}})
        return httpx.Response(200, json={"messages": [{"id": "wamid.local-test"}]})

    transport = httpx.MockTransport(local_response) if args.local else None
    async with httpx.AsyncClient(transport=transport) as client:
        provider = WhatsAppCloudProvider(
            access_token="local-test-token" if args.local else settings.WHATSAPP_ACCESS_TOKEN,
            phone_number_id="local-test-phone" if args.local else settings.WHATSAPP_PHONE_NUMBER_ID,
            api_version=settings.WHATSAPP_API_VERSION,
            client=client,
        )
        result = await provider.send_template(
            recipient_phone_number=args.recipient or "+15551234567",
            template_name=args.template,
            language=args.language,
            body_parameters=args.parameter,
        )
    return result.provider_message_id


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.local and args.scenario != "success":
        parser.error("--scenario requires --local")
    if args.send:
        if not args.recipient or not re.fullmatch(r"\+[1-9][0-9]{7,14}", args.recipient):
            parser.error("--send requires --recipient in E.164 format")
        if not args.confirm_opt_in:
            parser.error("--send requires --confirm-opt-in")
    if args.local:
        print("LOCAL SIMULATION: no Meta credentials, external network calls or real messages.")
        try:
            provider_message_id = asyncio.run(send_template(args))
        except MessageProviderError as error:
            print(f"Simulated failure [{error.error_code}]: {error}")
            return 1
        print(f"Simulated acceptance: {provider_message_id}")
        print(
            "No database writes or webhook delivery. Use the offline webhook tests to validate callbacks."
        )
        return 0
    required = (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
    )
    missing = [name for name in required if not getattr(settings, name)]
    for name in required:
        print(f"{name}: {'missing' if name in missing else 'configured'}")
    if missing:
        print("Set missing settings in the backend environment and recreate the API container.")
        return 1
    if not args.send:
        print(
            "Configuration present; no network request or message sent. Live connectivity is not verified."
        )
        return 0
    try:
        provider_message_id = asyncio.run(send_template(args))
    except MessageProviderError as error:
        print(f"Send failed [{error.error_code}]: {error}")
        return 1
    print(f"Meta accepted one message: {provider_message_id}")
    print(
        "Acceptance is not delivery. Confirm receipt and webhook events; this smoke message is not stored in admin history."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
