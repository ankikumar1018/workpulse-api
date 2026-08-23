"""Tests for application initialization."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"] == {"status": "healthy", "version": "0.1.0"}
    assert "timestamp" in body


def test_openapi_docs(client):
    """Test OpenAPI documentation endpoint."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_app_title():
    """Test app configuration."""
    assert app.title == "WorkPulse API"
    assert app.description == "Workforce communication automation platform"
