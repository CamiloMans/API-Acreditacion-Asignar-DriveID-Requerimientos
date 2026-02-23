"""Tests locales para la API con pytest."""
import os
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

# Variables requeridas por app.config al importar la aplicacion.
os.environ.setdefault("SUPABASE_PROJECT_ID", "local-test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxvY2FsLXRlc3QiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTUxNjIzOTAyMn0."
        "ZHVtbXktc2lnbmF0dXJl"
    ),
)

from app.main import app  # noqa: E402
from app.services.drive_service import drive_service  # noqa: E402
from app.services.supabase_service import supabase_service  # noqa: E402

client = TestClient(app)


DEFAULT_PARENT_CTX = {
    "parent_drive_id": "drive-123",
    "drive_name": "Proyectos 2026",
    "year": "2026",
}


def mock_resolve_parent_drive_context(codigo_proyecto: str) -> Dict[str, str]:
    assert codigo_proyecto == "MY-000-2026"
    return DEFAULT_PARENT_CTX


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "environment" in body


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["nombre"] == "API Asignar Folder ID a Requerimiento"
    assert body["endpoints"]["asignar_folder"] == "/asignar-folder"


def test_asignar_folder_empresa_myma(monkeypatch) -> None:
    def mock_resolve_acreditacion_root(
        codigo_proyecto: str,
        parent_ctx: Optional[Dict[str, str]] = None,
    ):
        assert codigo_proyecto == "MY-000-2026"
        assert parent_ctx == DEFAULT_PARENT_CTX
        return {
            "drive_id": "drive-123",
            "id_carpeta_acreditacion": "acreditacion-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Proyectos 2026",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
    ) -> Optional[str]:
        if folder_name == "02 MYMA":
            assert parent_id == "acreditacion-456"
            assert drive_id == "drive-123"
            return "folder-myma-001"
        return None

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert registro_id == 1
        assert drive_folder_id == "folder-myma-001"
        assert parent_drive_id == "drive-123"
        return True

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_resolve_parent_drive_context,
    )
    monkeypatch.setattr(
        drive_service,
        "resolve_acreditacion_root",
        mock_resolve_acreditacion_root,
    )
    monkeypatch.setattr(
        drive_service,
        "find_folder_exact_or_contains",
        mock_find_folder_exact_or_contains,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 1,
                "categoria_requerimiento": "Empresa",
                "empresa_acreditacion": "Myma",
                "nombre_trabajador": "Alan Flores",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["parent_drive_id"] == "drive-123"
    assert body["resumen"]["actualizados_exitosos"] == 1
    assert body["resumen"]["actualizados_fallidos"] == 0
    assert body["resumen"]["sin_drive_folder_id"] == 0
    assert body["registros"][0]["drive_folder_id_final"] == "folder-myma-001"
    assert body["registros"][0]["actualizado"] is True


def test_asignar_folder_no_empresa_prioriza_trabajador(monkeypatch) -> None:
    def mock_buscar_trabajador(codigo_proyecto: str, nombre_trabajador: str) -> Optional[str]:
        assert codigo_proyecto == "MY-000-2026"
        assert nombre_trabajador == "Diego Soto"
        return "folder-trab-123"

    def mock_buscar_conductor(codigo_proyecto: str, nombre_trabajador: str) -> Optional[str]:
        assert codigo_proyecto == "MY-000-2026"
        assert nombre_trabajador == "Diego Soto"
        return "folder-cond-999"

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert registro_id == 3
        # Debe priorizar trabajador sobre conductor.
        assert drive_folder_id == "folder-trab-123"
        assert parent_drive_id == "drive-123"
        return True

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_resolve_parent_drive_context,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_trabajador",
        mock_buscar_trabajador,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_conductor",
        mock_buscar_conductor,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 3,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": "Diego Soto",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["parent_drive_id"] == "drive-123"
    assert body["resumen"]["actualizados_exitosos"] == 1
    assert body["registros"][0]["drive_folder_id_trabajador"] == "folder-trab-123"
    assert body["registros"][0]["drive_folder_id_conductor"] == "folder-cond-999"
    assert body["registros"][0]["drive_folder_id_final"] == "folder-trab-123"


def test_asignar_folder_sin_drive_folder_id_actualiza_solo_parent(monkeypatch) -> None:
    update_calls: List[Dict[str, Any]] = []

    def mock_buscar_trabajador(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_buscar_conductor(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        update_calls.append(
            {
                "registro_id": registro_id,
                "drive_folder_id": drive_folder_id,
                "parent_drive_id": parent_drive_id,
            }
        )
        assert registro_id == 99
        assert drive_folder_id is None
        assert parent_drive_id == "drive-123"
        return True

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_resolve_parent_drive_context,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_trabajador",
        mock_buscar_trabajador,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_conductor",
        mock_buscar_conductor,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 99,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": "Sin Match",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["parent_drive_id"] == "drive-123"
    assert body["resumen"]["actualizados_exitosos"] == 0
    assert body["resumen"]["sin_drive_folder_id"] == 1
    assert body["registros"][0]["drive_folder_id_final"] is None
    assert body["registros"][0]["actualizado"] is False

    assert len(update_calls) == 1


def test_asignar_folder_parent_no_resoluble_continua(monkeypatch) -> None:
    def mock_parent_no_resoluble(_codigo_proyecto: str) -> None:
        return None

    def mock_buscar_trabajador(codigo_proyecto: str, nombre_trabajador: str) -> Optional[str]:
        assert codigo_proyecto == "MY-000-2026"
        assert nombre_trabajador == "Diego Soto"
        return "folder-trab-123"

    def mock_buscar_conductor(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert registro_id == 7
        assert drive_folder_id == "folder-trab-123"
        assert parent_drive_id is None
        return True

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_parent_no_resoluble,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_trabajador",
        mock_buscar_trabajador,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_conductor",
        mock_buscar_conductor,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 7,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": "Diego Soto",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["parent_drive_id"] is None
    assert body["resumen"]["actualizados_exitosos"] == 1
    assert body["resumen"]["sin_drive_folder_id"] == 0


def test_asignar_folder_request_mixto_comparte_parent(monkeypatch) -> None:
    update_calls: List[Dict[str, Any]] = []
    parent_calls = {"count": 0}

    def mock_resolve_parent(codigo_proyecto: str) -> Dict[str, str]:
        parent_calls["count"] += 1
        assert codigo_proyecto == "MY-000-2026"
        return DEFAULT_PARENT_CTX

    def mock_resolve_acreditacion_root(
        codigo_proyecto: str,
        parent_ctx: Optional[Dict[str, str]] = None,
    ):
        assert codigo_proyecto == "MY-000-2026"
        assert parent_ctx == DEFAULT_PARENT_CTX
        return {
            "drive_id": "drive-123",
            "id_carpeta_acreditacion": "acreditacion-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Proyectos 2026",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
    ) -> Optional[str]:
        if folder_name == "02 MYMA":
            assert parent_id == "acreditacion-456"
            assert drive_id == "drive-123"
            return "folder-myma-001"
        return None

    def mock_buscar_trabajador(_codigo_proyecto: str, nombre_trabajador: str) -> Optional[str]:
        if nombre_trabajador == "Diego Soto":
            return "folder-trab-123"
        return None

    def mock_buscar_conductor(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        update_calls.append(
            {
                "registro_id": registro_id,
                "drive_folder_id": drive_folder_id,
                "parent_drive_id": parent_drive_id,
            }
        )
        return True

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_resolve_parent,
    )
    monkeypatch.setattr(
        drive_service,
        "resolve_acreditacion_root",
        mock_resolve_acreditacion_root,
    )
    monkeypatch.setattr(
        drive_service,
        "find_folder_exact_or_contains",
        mock_find_folder_exact_or_contains,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_trabajador",
        mock_buscar_trabajador,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_conductor",
        mock_buscar_conductor,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 1,
                "categoria_requerimiento": "Empresa",
                "empresa_acreditacion": "Myma",
                "nombre_trabajador": "Alan Flores",
            },
            {
                "id": 3,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": "Diego Soto",
            },
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["parent_drive_id"] == "drive-123"
    assert body["resumen"]["actualizados_exitosos"] == 2
    assert body["resumen"]["sin_drive_folder_id"] == 0
    assert len(update_calls) == 2

    by_id = {call["registro_id"]: call for call in update_calls}
    assert by_id[1]["drive_folder_id"] == "folder-myma-001"
    assert by_id[3]["drive_folder_id"] == "folder-trab-123"
    assert by_id[1]["parent_drive_id"] == "drive-123"
    assert by_id[3]["parent_drive_id"] == "drive-123"
    assert parent_calls["count"] == 1


def test_asignar_folder_recupera_parent_desde_acreditacion(monkeypatch) -> None:
    parent_calls = {"count": 0}
    update_calls: List[Dict[str, Any]] = []

    def mock_resolve_parent(codigo_proyecto: str):
        assert codigo_proyecto == "MY-000-2026"
        parent_calls["count"] += 1
        # Primer intento falla (parent null), luego se recupera via acreditacion.
        if parent_calls["count"] == 1:
            return None
        return DEFAULT_PARENT_CTX

    def mock_resolve_acreditacion_root(
        codigo_proyecto: str,
        parent_ctx: Optional[Dict[str, str]] = None,
    ):
        assert codigo_proyecto == "MY-000-2026"
        assert parent_ctx is None
        return {
            "drive_id": "drive-123",
            "id_carpeta_acreditacion": "acreditacion-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Proyectos 2026",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
    ) -> Optional[str]:
        if folder_name == "02 MYMA":
            assert parent_id == "acreditacion-456"
            assert drive_id == "drive-123"
            return "folder-myma-001"
        return None

    def mock_buscar_trabajador(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return "folder-trab-123"

    def mock_buscar_conductor(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        update_calls.append(
            {
                "registro_id": registro_id,
                "drive_folder_id": drive_folder_id,
                "parent_drive_id": parent_drive_id,
            }
        )
        return True

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_resolve_parent,
    )
    monkeypatch.setattr(
        drive_service,
        "resolve_acreditacion_root",
        mock_resolve_acreditacion_root,
    )
    monkeypatch.setattr(
        drive_service,
        "find_folder_exact_or_contains",
        mock_find_folder_exact_or_contains,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_trabajador",
        mock_buscar_trabajador,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_conductor",
        mock_buscar_conductor,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 1,
                "categoria_requerimiento": "Empresa",
                "empresa_acreditacion": "Myma",
                "nombre_trabajador": None,
            },
            {
                "id": 2,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": "Diego Soto",
            },
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["parent_drive_id"] == "drive-123"
    assert len(update_calls) == 2
    assert update_calls[0]["parent_drive_id"] == "drive-123"
    assert update_calls[1]["parent_drive_id"] == "drive-123"
