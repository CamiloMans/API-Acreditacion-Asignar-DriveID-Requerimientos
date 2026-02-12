"""Tests básicos para la API."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    """Test del endpoint raíz."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["status"] == "running"


def test_health():
    """Test del endpoint de health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_crear_carpetas_invalid_code():
    """Test del endpoint crear carpetas con código inválido."""
    response = client.post(
        "/carpetas/crear",
        json={
            "codigo_proyecto": "INVALID-CODE",
            "myma": {
                "especialistas": [],
                "conductores": [],
                "vehiculos": []
            },
            "externo": {
                "empresa": "Test",
                "especialistas": [],
                "conductores": [],
                "vehiculos": []
            }
        }
    )
    assert response.status_code == 422  # Validation error


def test_crear_carpetas_missing_fields():
    """Test del endpoint crear carpetas con campos faltantes."""
    response = client.post(
        "/carpetas/crear",
        json={
            "codigo_proyecto": "MY-000-2026"
        }
    )
    assert response.status_code == 422  # Validation error

