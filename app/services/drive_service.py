"""Servicio para resolver carpetas en Google Drive."""
import logging
import os
import re
import time
import unicodedata
from typing import Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
ACREDITACIONES_DRIVE_NAME = "Acreditaciones"
ACREDITACIONES_ROOT_FOLDER_NAME = "Acreditaciones"
NUMERIC_PREFIX_PATTERN = re.compile(r"^\s*\d+\s*[-_.]?\s*")


class DriveService:
    """Servicio para operaciones de lectura en Google Drive."""

    def __init__(self):
        self.client_secret_file = settings.GOOGLE_CLIENT_SECRET_FILE
        self.token_file = settings.GOOGLE_TOKEN_FILE
        self.service = None

    @staticmethod
    def _normalize_name(value: str) -> str:
        """Normaliza texto para comparaciones case-insensitive y sin tildes."""
        normalized = unicodedata.normalize("NFD", value or "")
        without_accents = "".join(
            ch for ch in normalized if unicodedata.category(ch) != "Mn"
        )
        collapsed_spaces = " ".join(without_accents.strip().split())
        return collapsed_spaces.casefold()

    def _normalize_base_folder_label(self, value: str) -> str:
        """Normaliza etiqueta base ignorando prefijos numericos (01, 02, ...)."""
        normalized = self._normalize_name(value)
        return NUMERIC_PREFIX_PATTERN.sub("", normalized)

    def _match_folder_name(
        self,
        actual_name: str,
        expected_name: str,
        ignore_numeric_prefix: bool = False,
    ) -> bool:
        """Compara nombres de carpeta con normalizacion configurable."""
        if ignore_numeric_prefix:
            return (
                self._normalize_base_folder_label(actual_name)
                == self._normalize_base_folder_label(expected_name)
            )
        return self._normalize_name(actual_name) == self._normalize_name(expected_name)

    def get_service(self):
        """Obtiene un cliente autenticado de Google Drive API."""
        if self.service is not None:
            return self.service

        creds = None

        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_file,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self.service

    def _execute_with_retry(self, request, max_retries: int = 5):
        """Ejecuta una request con backoff para errores transitorios."""
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as error:
                status = getattr(error.resp, "status", None)
                if status in [429, 500, 503] and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Google Drive API status %s. Reintentando en %ss (intento %s/%s)",
                        status,
                        wait_time,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as error:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Google Drive API error transitorio: %s. Reintentando en %ss "
                        "(intento %s/%s)",
                        error,
                        wait_time,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(wait_time)
                    continue
                raise

    def find_shared_drive_by_name(self, drive_name: str) -> Optional[str]:
        """Busca un Shared Drive por nombre y retorna su ID."""
        service = self.get_service()
        page_token = None

        while True:
            try:
                results = self._execute_with_retry(
                    service.drives().list(pageSize=100, pageToken=page_token)
                )
            except Exception as error:
                logger.error("Error buscando Shared Drive '%s': %s", drive_name, error)
                return None

            for drive in results.get("drives", []):
                if self._match_folder_name(drive.get("name", ""), drive_name):
                    return drive.get("id")

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return None

    def list_folders_in_directory(
        self,
        parent_id: str,
        drive_id: Optional[str] = None,
        max_results: int = 1000,
    ) -> List[Tuple[str, str]]:
        """Lista carpetas dentro de un directorio."""
        service = self.get_service()
        folders: List[Tuple[str, str]] = []
        page_token = None

        if drive_id and parent_id == drive_id:
            query = (
                "mimeType = 'application/vnd.google-apps.folder' and "
                f"'{drive_id}' in parents and trashed = false"
            )
        else:
            query = (
                "mimeType = 'application/vnd.google-apps.folder' and "
                f"'{parent_id}' in parents and trashed = false"
            )

        while True:
            params = {
                "q": query,
                "spaces": "drive",
                "fields": "nextPageToken, files(id, name, parents)",
                "pageToken": page_token,
                "pageSize": 100,
                "orderBy": "name",
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }

            if drive_id:
                params["driveId"] = drive_id
                params["corpora"] = "drive"

            try:
                results = self._execute_with_retry(service.files().list(**params))
            except Exception as error:
                logger.error("Error listando carpetas en parent_id=%s: %s", parent_id, error)
                return folders

            for item in results.get("files", []):
                folders.append((item["name"], item["id"]))
                if len(folders) >= max_results:
                    return folders

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return folders

    def find_folder_by_name_in_directory(
        self,
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        """Busca una carpeta por nombre exacto dentro de un directorio."""
        service = self.get_service()
        escaped_name = folder_name.replace("'", "\\'")

        if drive_id and parent_id == drive_id:
            query = (
                f"name = '{escaped_name}' and "
                "mimeType = 'application/vnd.google-apps.folder' and "
                f"'{drive_id}' in parents and trashed = false"
            )
        else:
            query = (
                f"name = '{escaped_name}' and "
                "mimeType = 'application/vnd.google-apps.folder' and "
                f"'{parent_id}' in parents and trashed = false"
            )

        page_token = None
        while True:
            params = {
                "q": query,
                "spaces": "drive",
                "fields": "nextPageToken, files(id, name, parents)",
                "pageToken": page_token,
                "pageSize": 100,
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }

            if drive_id:
                params["driveId"] = drive_id
                params["corpora"] = "drive"

            try:
                results = self._execute_with_retry(service.files().list(**params))
            except Exception as error:
                logger.error(
                    "Error buscando carpeta '%s' en parent_id=%s: %s",
                    folder_name,
                    parent_id,
                    error,
                )
                return None

            for item in results.get("files", []):
                if self._match_folder_name(
                    item.get("name", ""),
                    folder_name,
                    ignore_numeric_prefix=ignore_numeric_prefix,
                ):
                    return item.get("id")

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return None

    def find_folder_by_normalized_name_in_directory(
        self,
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        """Busca carpeta por normalizacion (sin tildes, case-insensitive)."""
        folders = self.list_folders_in_directory(parent_id, drive_id)
        for name, folder_id in folders:
            if self._match_folder_name(
                name,
                folder_name,
                ignore_numeric_prefix=ignore_numeric_prefix,
            ):
                return folder_id
        return None

    def find_folder_containing_name(
        self,
        folder_name_part: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        """Busca una carpeta por coincidencia parcial normalizada."""
        folders = self.list_folders_in_directory(parent_id, drive_id)
        if ignore_numeric_prefix:
            search = self._normalize_base_folder_label(folder_name_part)
        else:
            search = self._normalize_name(folder_name_part)
        for name, folder_id in folders:
            if ignore_numeric_prefix:
                candidate = self._normalize_base_folder_label(name)
            else:
                candidate = self._normalize_name(name)
            if search in candidate:
                return folder_id
        return None

    def find_folder_exact_or_contains(
        self,
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
        ignore_numeric_prefix: bool = False,
    ) -> Optional[str]:
        """Busca carpeta: exacto, luego normalizado y finalmente contains."""
        exact_id = self.find_folder_by_name_in_directory(
            folder_name,
            parent_id,
            drive_id,
            ignore_numeric_prefix=ignore_numeric_prefix,
        )
        if exact_id:
            return exact_id

        normalized_id = self.find_folder_by_normalized_name_in_directory(
            folder_name,
            parent_id,
            drive_id,
            ignore_numeric_prefix=ignore_numeric_prefix,
        )
        if normalized_id:
            return normalized_id

        return self.find_folder_containing_name(
            folder_name,
            parent_id,
            drive_id,
            ignore_numeric_prefix=ignore_numeric_prefix,
        )

    def resolve_parent_drive_context(self, codigo_proyecto: str) -> Optional[Dict[str, str]]:
        """
        Resuelve contexto base desde el Shared Drive central de Acreditaciones.
        """
        match = re.match(r"^MY-\d{3}-(\d{4})$", codigo_proyecto)
        if not match:
            logger.warning(
                "codigo_proyecto '%s' no cumple formato esperado MY-XXX-YYYY",
                codigo_proyecto,
            )
            return None

        year = match.group(1)
        drive_name = ACREDITACIONES_DRIVE_NAME
        parent_drive_id = self.find_shared_drive_by_name(drive_name)
        if not parent_drive_id:
            logger.error("No se encontro Shared Drive '%s'", drive_name)
            return None

        return {
            "parent_drive_id": parent_drive_id,
            "drive_name": drive_name,
            "year": year,
        }

    def resolve_acreditacion_root(
        self,
        codigo_proyecto: str,
        parent_ctx: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, str]]:
        """
        Resuelve IDs para:
        Acreditaciones (Shared Drive) -> Acreditaciones -> Proyectos YYYY -> MY-XXX-YYYY

        Si se recibe parent_ctx, reutiliza ese contexto anual ya resuelto para evitar
        consultas duplicadas al resolver el Shared Drive de Acreditaciones.
        """
        resolved_parent_ctx = parent_ctx or self.resolve_parent_drive_context(codigo_proyecto)
        if not resolved_parent_ctx:
            return None

        drive_id = resolved_parent_ctx["parent_drive_id"]
        year = resolved_parent_ctx["year"]
        drive_name = resolved_parent_ctx["drive_name"]
        current_parent = drive_id
        route_candidates = [
            [ACREDITACIONES_ROOT_FOLDER_NAME],
            [f"Proyectos {year}"],
            [codigo_proyecto],
        ]
        resolved_ids: List[str] = []

        for level_options in route_candidates:
            folder_id = None
            for level_name in level_options:
                folder_id = self.find_folder_exact_or_contains(
                    level_name,
                    current_parent,
                    drive_id,
                )
                if folder_id:
                    break

            if not folder_id:
                logger.warning(
                    "No se encontro ninguna carpeta %s dentro de parent_id=%s en drive_id=%s",
                    level_options,
                    current_parent,
                    drive_id,
                )
                return None
            current_parent = folder_id
            resolved_ids.append(folder_id)

        carpeta_acreditaciones_id, carpeta_proyectos_anio_id, carpeta_proyecto_id = resolved_ids

        return {
            "drive_id": drive_id,
            "id_carpeta_acreditaciones": carpeta_acreditaciones_id,
            "id_carpeta_proyectos_anio": carpeta_proyectos_anio_id,
            "id_carpeta_proyecto": carpeta_proyecto_id,
            # Se mantiene por compatibilidad: ahora apunta a la carpeta del proyecto.
            "id_carpeta_acreditacion": carpeta_proyecto_id,
            "codigo_proyecto": codigo_proyecto,
            "year": year,
            "drive_name": drive_name,
        }

drive_service = DriveService()

