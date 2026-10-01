"""Tests for Meta WhatsApp webhook verification and signature validation."""

import hashlib
import hmac

from fastapi.testclient import TestClient

from app.api.dependencies import get_message_service
from app.domain.enums import DeliveryStatus
from app.main import create_app
from core.config import settings


def signed_payload(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_webhook_verification_returns_meta_challenge(monkeypatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "verify-token")
    app = create_app()

    response = TestClient(app).get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-token",
            "hub.challenge": "challenge-value",
        },
    )

    assert response.status_code == 200
    assert response.text == "challenge-value"


def test_webhook_rejects_an_invalid_signature(monkeypatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "app-secret")
    app = create_app()

    response = TestClient(app).post(
        "/api/v1/webhooks/whatsapp",
        content=b'{"entry": []}',
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )

    assert response.status_code == 401


def test_webhook_accepts_a_valid_signature(monkeypatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "app-secret")
    payload = b'{"entry": []}'
    signature = "sha256=" + hmac.new(b"app-secret", payload, hashlib.sha256).hexdigest()
    app = create_app()

    response = TestClient(app).post(
        "/api/v1/webhooks/whatsapp",
        content=payload,
        headers={"X-Hub-Signature-256": signature},
    )

    assert response.status_code == 204


def test_webhook_applies_recognized_statuses_and_error_codes(monkeypatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "app-secret")
    payload = (
        b'{"entry":[{"changes":[{"value":{"statuses":['
        b'{"id":"wamid.sent","status":"sent"},'
        b'{"id":"wamid.failed","status":"failed","errors":[{"code":131026}]}'
        b"]}}]}]}"
    )

    class FakeMessageService:
        def __init__(self):
            self.calls = []

        async def apply_provider_status(self, **kwargs):
            self.calls.append(kwargs)

    service = FakeMessageService()
    app = create_app()
    app.dependency_overrides[get_message_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/v1/webhooks/whatsapp",
            content=payload,
            headers={"X-Hub-Signature-256": signed_payload(payload, "app-secret")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert service.calls == [
        {
            "provider_name": "whatsapp_cloud",
            "provider_message_id": "wamid.sent",
            "new_status": DeliveryStatus.SENT,
            "error_code": None,
        },
        {
            "provider_name": "whatsapp_cloud",
            "provider_message_id": "wamid.failed",
            "new_status": DeliveryStatus.FAILED,
            "error_code": "131026",
        },
    ]


def test_webhook_ignores_unknown_or_malformed_status_events(monkeypatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "app-secret")
    payload = (
        b'{"entry":[{"changes":[{"value":{"statuses":['
        b'{"id":"wamid.unknown","status":"read"},'
        b'{"id":123,"status":"delivered"},'
        b'{"id":"wamid.valid","status":"delivered"}'
        b"]}}]}]}"
    )

    class FakeMessageService:
        def __init__(self):
            self.calls = []

        async def apply_provider_status(self, **kwargs):
            self.calls.append(kwargs)

    service = FakeMessageService()
    app = create_app()
    app.dependency_overrides[get_message_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/v1/webhooks/whatsapp",
            content=payload,
            headers={"X-Hub-Signature-256": signed_payload(payload, "app-secret")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert service.calls == [
        {
            "provider_name": "whatsapp_cloud",
            "provider_message_id": "wamid.valid",
            "new_status": DeliveryStatus.DELIVERED,
            "error_code": None,
        }
    ]


def test_webhook_rejects_invalid_verification_parameters(monkeypatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "verify-token")
    app = create_app()

    response = TestClient(app).get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge-value",
        },
    )

    assert response.status_code == 403
