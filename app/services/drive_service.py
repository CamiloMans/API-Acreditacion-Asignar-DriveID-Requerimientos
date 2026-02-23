"""Servicio para resolver carpetas en Google Drive."""
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveService:
    """Servicio para operaciones de lectura en Google Drive."""

    def __init__(self):
        self.client_secret_file = settings.GOOGLE_CLIENT_SECRET_FILE
        self.token_file = settings.GOOGLE_TOKEN_FILE
        self.service = None

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
                if drive.get("name") == drive_name:
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
                if item.get("name") == folder_name:
                    return item.get("id")

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return None

    def find_folder_containing_name(
        self,
        folder_name_part: str,
        parent_id: str,
        drive_id: Optional[str] = None,
    ) -> Optional[str]:
        """Busca una carpeta por coincidencia parcial (case-insensitive)."""
        folders = self.list_folders_in_directory(parent_id, drive_id)
        search = folder_name_part.strip().lower()
        for name, folder_id in folders:
            if search in name.lower():
                return folder_id
        return None

    def find_folder_exact_or_contains(
        self,
        folder_name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
    ) -> Optional[str]:
        """Busca carpeta: primero exacto, luego contains."""
        exact_id = self.find_folder_by_name_in_directory(folder_name, parent_id, drive_id)
        if exact_id:
            return exact_id
        return self.find_folder_containing_name(folder_name, parent_id, drive_id)

    def resolve_parent_drive_context(self, codigo_proyecto: str) -> Optional[Dict[str, str]]:
        """
        Resuelve el Shared Drive anual:
        codigo_proyecto MY-XXX-YYYY -> Shared Drive Proyectos YYYY
        """
        match = re.match(r"^MY-\d{3}-(\d{4})$", codigo_proyecto)
        if not match:
            logger.warning(
                "codigo_proyecto '%s' no cumple formato esperado MY-XXX-YYYY",
                codigo_proyecto,
            )
            return None

        year = match.group(1)
        drive_name = f"Proyectos {year}"
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
        Proyectos YYYY -> MY-XXX-YYYY -> 08 Terrenos -> 03 Acreditacion y Arranque -> 01 Acreditacion

        Si se recibe parent_ctx, reutiliza ese contexto anual ya resuelto para evitar
        consultas duplicadas al resolver el Shared Drive.
        """
        resolved_parent_ctx = parent_ctx or self.resolve_parent_drive_context(codigo_proyecto)
        if not resolved_parent_ctx:
            return None

        drive_id = resolved_parent_ctx["parent_drive_id"]
        year = resolved_parent_ctx["year"]
        drive_name = resolved_parent_ctx["drive_name"]
        current_parent = drive_id
        route_candidates = [
            [codigo_proyecto],
            ["08 Terrenos"],
            ["03 Acreditación y Arranque", "03 Acreditacion y Arranque"],
            ["01 Acreditación", "01 Acreditacion"],
        ]

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

        return {
            "drive_id": drive_id,
            "id_carpeta_acreditacion": current_parent,
            "codigo_proyecto": codigo_proyecto,
            "year": year,
            "drive_name": drive_name,
        }


drive_service = DriveService()
