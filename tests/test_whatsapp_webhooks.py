"""Tests for Meta WhatsApp webhook verification and signature validation."""

import hashlib
import hmac

from fastapi.testclient import TestClient

from app.main import create_app
from core.config import settings


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
