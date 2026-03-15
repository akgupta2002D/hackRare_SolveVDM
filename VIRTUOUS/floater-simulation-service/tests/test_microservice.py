"""
Checks that the microservice is working: root and health routes return
expected status and body. Run with: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_200_and_service_name():
    """Root route should return 200 and include the service name."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("service") == "floater-simulation-service"
    assert "message" in data


def test_health_returns_200_and_ok():
    """Health route should return 200 and message 'ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("message") == "ok"
    assert data.get("service") == "floater-simulation-service"
