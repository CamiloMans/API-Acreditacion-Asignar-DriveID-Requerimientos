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
    "drive_name": "Acreditaciones",
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
            "id_carpeta_acreditacion": "proyecto-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Acreditaciones",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        if folder_name == "MYMA":
            assert parent_id == "proyecto-456"
            assert drive_id == "drive-123"
            return "myma-789"
        if folder_name == "01 Empresa":
            assert parent_id == "myma-789"
            assert drive_id == "drive-123"
            assert ignore_numeric_prefix is True
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


def test_asignar_folder_empresa_externa_busca_01_empresa(monkeypatch) -> None:
    def mock_resolve_acreditacion_root(
        codigo_proyecto: str,
        parent_ctx: Optional[Dict[str, str]] = None,
    ):
        assert codigo_proyecto == "MY-000-2026"
        assert parent_ctx == DEFAULT_PARENT_CTX
        return {
            "drive_id": "drive-123",
            "id_carpeta_acreditacion": "proyecto-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Acreditaciones",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        if folder_name == "Externos":
            assert parent_id == "proyecto-456"
            assert drive_id == "drive-123"
            return "externos-001"
        if folder_name == "NLT":
            assert parent_id == "externos-001"
            assert drive_id == "drive-123"
            return "empresa-nlt-001"
        if folder_name == "01 Empresa":
            assert parent_id == "empresa-nlt-001"
            assert drive_id == "drive-123"
            assert ignore_numeric_prefix is True
            return "folder-nlt-empresa-001"
        return None

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert registro_id == 2
        assert drive_folder_id == "folder-nlt-empresa-001"
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
                "id": 2,
                "categoria_requerimiento": "Empresa",
                "empresa_acreditacion": "NLT",
                "nombre_trabajador": None,
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["parent_drive_id"] == "drive-123"
    assert body["resumen"]["actualizados_exitosos"] == 1
    assert body["resumen"]["sin_drive_folder_id"] == 0
    assert body["registros"][0]["drive_folder_id_final"] == "folder-nlt-empresa-001"


def test_drive_service_resolve_parent_drive_context_usa_acreditaciones(monkeypatch) -> None:
    def mock_find_shared_drive_by_name(drive_name: str) -> Optional[str]:
        assert drive_name == "Acreditaciones"
        return "drive-acreditaciones"

    monkeypatch.setattr(
        drive_service,
        "find_shared_drive_by_name",
        mock_find_shared_drive_by_name,
    )

    result = drive_service.resolve_parent_drive_context("MY-000-2026")
    assert result is not None
    assert result["parent_drive_id"] == "drive-acreditaciones"
    assert result["drive_name"] == "Acreditaciones"
    assert result["year"] == "2026"


def test_drive_service_resolve_acreditacion_root_con_ruta_nueva(monkeypatch) -> None:
    def mock_resolve_parent(_codigo_proyecto: str) -> Dict[str, str]:
        return {
            "parent_drive_id": "drive-acreditaciones",
            "drive_name": "Acreditaciones",
            "year": "2026",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        assert drive_id == "drive-acreditaciones"
        assert ignore_numeric_prefix is False
        if folder_name == "Acreditaciones":
            assert parent_id == "drive-acreditaciones"
            return "acreditaciones-root"
        if folder_name == "Proyectos 2026":
            assert parent_id == "acreditaciones-root"
            return "proyectos-2026"
        if folder_name == "MY-000-2026":
            assert parent_id == "proyectos-2026"
            return "my-000-2026"
        return None

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_resolve_parent,
    )
    monkeypatch.setattr(
        drive_service,
        "find_folder_exact_or_contains",
        mock_find_folder_exact_or_contains,
    )

    result = drive_service.resolve_acreditacion_root("MY-000-2026")
    assert result is not None
    assert result["drive_id"] == "drive-acreditaciones"
    assert result["id_carpeta_acreditaciones"] == "acreditaciones-root"
    assert result["id_carpeta_proyectos_anio"] == "proyectos-2026"
    assert result["id_carpeta_proyecto"] == "my-000-2026"
    assert result["id_carpeta_acreditacion"] == "my-000-2026"


def test_drive_service_find_folder_normaliza_y_ignora_prefijo_numerico(monkeypatch) -> None:
    def mock_find_folder_by_name_in_directory(
        _folder_name: str,
        _parent_id: str,
        _drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        _ = ignore_numeric_prefix
        return None

    def mock_list_folders_in_directory(
        _parent_id: str,
        _drive_id: Optional[str] = None,
        _max_results: int = 1000,
    ) -> List[Any]:
        return [
            ("01 Empreśa", "folder-empresa-001"),
            ("nlt", "folder-nlt-001"),
        ]

    monkeypatch.setattr(
        drive_service,
        "find_folder_by_name_in_directory",
        mock_find_folder_by_name_in_directory,
    )
    monkeypatch.setattr(
        drive_service,
        "list_folders_in_directory",
        mock_list_folders_in_directory,
    )

    empresa_folder = drive_service.find_folder_exact_or_contains(
        "01 Empresa",
        "parent-001",
        "drive-001",
        ignore_numeric_prefix=True,
    )
    contratista_folder = drive_service.find_folder_exact_or_contains(
        "NLT",
        "parent-001",
        "drive-001",
    )

    assert empresa_folder == "folder-empresa-001"
    assert contratista_folder == "folder-nlt-001"


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
            "id_carpeta_acreditacion": "proyecto-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Acreditaciones",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        if folder_name == "MYMA":
            assert parent_id == "proyecto-456"
            assert drive_id == "drive-123"
            return "myma-789"
        if folder_name == "01 Empresa":
            assert parent_id == "myma-789"
            assert drive_id == "drive-123"
            assert ignore_numeric_prefix is True
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


def test_asignar_folder_cachea_lookups_repetidos(monkeypatch) -> None:
    parent_calls = {"count": 0}
    acreditacion_calls = {"count": 0}
    find_folder_calls: List[Dict[str, Any]] = []
    trabajador_calls: List[str] = []
    conductor_calls: List[str] = []

    def mock_resolve_parent(codigo_proyecto: str) -> Dict[str, str]:
        parent_calls["count"] += 1
        assert codigo_proyecto == "MY-000-2026"
        return DEFAULT_PARENT_CTX

    def mock_resolve_acreditacion_root(
        codigo_proyecto: str,
        parent_ctx: Optional[Dict[str, str]] = None,
    ):
        acreditacion_calls["count"] += 1
        assert codigo_proyecto == "MY-000-2026"
        assert parent_ctx == DEFAULT_PARENT_CTX
        return {
            "drive_id": "drive-123",
            "id_carpeta_acreditacion": "proyecto-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Acreditaciones",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        find_folder_calls.append(
            {
                "folder_name": folder_name,
                "parent_id": parent_id,
                "drive_id": drive_id,
                "ignore_numeric_prefix": ignore_numeric_prefix,
            }
        )
        if folder_name == "MYMA":
            return "myma-789"
        if folder_name == "Externos":
            return "externos-111"
        if folder_name == "Econsult Ambiental":
            return "econsult-222"
        if folder_name == "01 Empresa" and parent_id == "myma-789":
            return "folder-myma-001"
        if folder_name == "01 Empresa" and parent_id == "econsult-222":
            return "folder-econsult-001"
        return None

    def mock_buscar_trabajador(_codigo_proyecto: str, nombre_trabajador: str) -> Optional[str]:
        trabajador_calls.append(nombre_trabajador)
        if nombre_trabajador == "Ailan Villalon Cueto":
            return "folder-trab-ailan"
        if nombre_trabajador == "Alan Flores":
            return "folder-trab-alan"
        return None

    def mock_buscar_conductor(_codigo_proyecto: str, nombre_trabajador: str) -> Optional[str]:
        conductor_calls.append(nombre_trabajador)
        return None

    def mock_actualizar(
        _registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert drive_folder_id is not None
        assert parent_drive_id == "drive-123"
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
                "categoria_requerimiento": "Empresa",
                "empresa_acreditacion": "MyMA",
                "nombre_trabajador": None,
            },
            {
                "id": 3,
                "categoria_requerimiento": "Empresa",
                "empresa_acreditacion": "Econsult Ambiental",
                "nombre_trabajador": None,
            },
            {
                "id": 4,
                "categoria_requerimiento": "Empresa",
                "empresa_acreditacion": "Econsult Ambiental",
                "nombre_trabajador": None,
            },
            {
                "id": 5,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "Myma",
                "nombre_trabajador": "Ailan Villalon Cueto",
            },
            {
                "id": 6,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "Myma",
                "nombre_trabajador": "Alan Flores",
            },
            {
                "id": 7,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "Myma",
                "nombre_trabajador": "Ailan Villalon Cueto",
            },
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["resumen"]["actualizados_exitosos"] == 7
    assert parent_calls["count"] == 1
    assert acreditacion_calls["count"] == 1
    assert len(find_folder_calls) == 5
    assert sorted(trabajador_calls) == ["Ailan Villalon Cueto", "Alan Flores"]
    assert sorted(conductor_calls) == ["Ailan Villalon Cueto", "Alan Flores"]


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
            "id_carpeta_acreditacion": "proyecto-456",
            "codigo_proyecto": codigo_proyecto,
            "year": "2026",
            "drive_name": "Acreditaciones",
        }

    def mock_find_folder_exact_or_contains(
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        if folder_name == "MYMA":
            assert parent_id == "proyecto-456"
            assert drive_id == "drive-123"
            return "myma-789"
        if folder_name == "01 Empresa":
            assert parent_id == "myma-789"
            assert drive_id == "drive-123"
            assert ignore_numeric_prefix is True
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


def test_asignar_folder_categoria_vehiculos_busca_por_patente(monkeypatch) -> None:
    def mock_buscar_vehiculo(id_proyecto: int, patente_vehiculo: str) -> Optional[str]:
        assert id_proyecto == 123
        assert patente_vehiculo == "ABCD12"
        return "folder-veh-001"

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert registro_id == 10
        assert drive_folder_id == "folder-veh-001"
        assert parent_drive_id == "drive-123"
        return True

    monkeypatch.setattr(
        drive_service,
        "resolve_parent_drive_context",
        mock_resolve_parent_drive_context,
    )
    monkeypatch.setattr(
        supabase_service,
        "buscar_drive_folder_id_vehiculo",
        mock_buscar_vehiculo,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "id_proyecto": 123,
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 10,
                "categoria_requerimiento": "Vehículos",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": None,
                "patente_vehiculo": "  ABCD12  ",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["resumen"]["actualizados_exitosos"] == 1
    assert body["registros"][0]["drive_folder_id_vehiculo"] == "folder-veh-001"
    assert body["registros"][0]["drive_folder_id_final"] == "folder-veh-001"
    assert body["registros"][0]["nombre_trabajador"] is None


def test_asignar_folder_categoria_vehiculo_sin_patente_devuelve_422() -> None:
    payload = {
        "id_proyecto": 123,
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 11,
                "categoria_requerimiento": "Vehiculo",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": None,
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 422


def test_asignar_folder_no_empresa_sin_nombre_trabajador_devuelve_422() -> None:
    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 12,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": None,
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 422


def test_asignar_folder_vehiculo_sin_id_proyecto_devuelve_422() -> None:
    payload = {
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 13,
                "categoria_requerimiento": "Vehiculos",
                "empresa_acreditacion": "AGQ",
                "patente_vehiculo": "ABCD12",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 422


def test_asignar_folder_fallback_a_vehiculo_si_no_hay_trabajador_ni_conductor(monkeypatch) -> None:
    def mock_buscar_trabajador(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_buscar_conductor(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_buscar_vehiculo(id_proyecto: int, patente_vehiculo: str) -> Optional[str]:
        assert id_proyecto == 123
        assert patente_vehiculo == "XZ99AA"
        return "folder-veh-fallback"

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert registro_id == 14
        assert drive_folder_id == "folder-veh-fallback"
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
        "buscar_drive_folder_id_vehiculo",
        mock_buscar_vehiculo,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "id_proyecto": 123,
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 14,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": "Diego Soto",
                "patente_vehiculo": "XZ99AA",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["registros"][0]["drive_folder_id_trabajador"] is None
    assert body["registros"][0]["drive_folder_id_conductor"] is None
    assert body["registros"][0]["drive_folder_id_vehiculo"] == "folder-veh-fallback"
    assert body["registros"][0]["drive_folder_id_final"] == "folder-veh-fallback"


def test_asignar_folder_prioriza_trabajador_sobre_vehiculo(monkeypatch) -> None:
    def mock_buscar_trabajador(_codigo_proyecto: str, nombre_trabajador: str) -> Optional[str]:
        assert nombre_trabajador == "Diego Soto"
        return "folder-trab-priority"

    def mock_buscar_conductor(_codigo_proyecto: str, _nombre_trabajador: str) -> Optional[str]:
        return None

    def mock_buscar_vehiculo(_id_proyecto: int, _patente_vehiculo: str) -> Optional[str]:
        raise AssertionError("No debe consultar vehiculo si ya encontro trabajador")

    def mock_actualizar(
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        assert registro_id == 15
        assert drive_folder_id == "folder-trab-priority"
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
        "buscar_drive_folder_id_vehiculo",
        mock_buscar_vehiculo,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "id_proyecto": 123,
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 15,
                "categoria_requerimiento": "Persona",
                "empresa_acreditacion": "AGQ",
                "nombre_trabajador": "Diego Soto",
                "patente_vehiculo": "ZZ11ZZ",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["registros"][0]["drive_folder_id_trabajador"] == "folder-trab-priority"
    assert body["registros"][0]["drive_folder_id_vehiculo"] is None
    assert body["registros"][0]["drive_folder_id_final"] == "folder-trab-priority"


def test_asignar_folder_vehiculo_sin_match_actualiza_solo_parent(monkeypatch) -> None:
    update_calls: List[Dict[str, Any]] = []

    def mock_buscar_vehiculo(id_proyecto: int, patente_vehiculo: str) -> Optional[str]:
        assert id_proyecto == 123
        assert patente_vehiculo == "NOPE01"
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
        assert registro_id == 16
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
        "buscar_drive_folder_id_vehiculo",
        mock_buscar_vehiculo,
    )
    monkeypatch.setattr(
        supabase_service,
        "actualizar_brg_acreditacion_solicitud_requerimiento",
        mock_actualizar,
    )

    payload = {
        "id_proyecto": 123,
        "codigo_proyecto": "MY-000-2026",
        "registros": [
            {
                "id": 16,
                "categoria_requerimiento": "Vehiculo",
                "empresa_acreditacion": "AGQ",
                "patente_vehiculo": "NOPE01",
            }
        ],
    }

    response = client.post("/asignar-folder", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["resumen"]["actualizados_exitosos"] == 0
    assert body["resumen"]["sin_drive_folder_id"] == 1
    assert body["registros"][0]["drive_folder_id_vehiculo"] is None
    assert body["registros"][0]["drive_folder_id_final"] is None
    assert body["registros"][0]["actualizado"] is False
    assert len(update_calls) == 1
