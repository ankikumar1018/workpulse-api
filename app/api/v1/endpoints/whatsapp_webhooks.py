"""Meta WhatsApp webhook verification and delivery-status processing."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.dependencies import MessageSvc
from app.domain.enums import DeliveryStatus
from core.config import settings

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])
_STATUS_MAP = {
    "sent": DeliveryStatus.SENT,
    "delivered": DeliveryStatus.DELIVERED,
    "failed": DeliveryStatus.FAILED,
}


def _is_valid_signature(body: bytes, signature: str | None) -> bool:
    if not settings.WHATSAPP_APP_SECRET or not signature:
        return False
    expected = "sha256=" + hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.get("")
async def verify_webhook(request: Request) -> Response:
    """Complete Meta's webhook subscription handshake."""
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        and hmac.compare_digest(
            params.get("hub.verify_token", ""), settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        )
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook verification failed")


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def receive_webhook(request: Request, controller: MessageSvc) -> Response:
    """Verify and idempotently apply recognized WhatsApp delivery events."""
    body = await request.body()
    if not _is_valid_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    payload: dict[str, Any] = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for event in change.get("value", {}).get("statuses", []):
                delivery_status = _STATUS_MAP.get(event.get("status"))
                message_id = event.get("id")
                if delivery_status and isinstance(message_id, str):
                    errors = event.get("errors", [])
                    error_code = str(errors[0].get("code")) if errors else None
                    await controller.apply_provider_status(
                        provider_name="whatsapp_cloud",
                        provider_message_id=message_id,
                        new_status=delivery_status,
                        error_code=error_code,
                    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
