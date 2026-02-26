"""Servicio para interactuar con Supabase."""
import logging
from typing import Any, Dict, Optional

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Servicio para operaciones con Supabase."""

    def __init__(self):
        """Inicializa el cliente de Supabase."""
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info(
            "Cliente Supabase inicializado para proyecto: %s",
            settings.SUPABASE_PROJECT_ID,
        )

    def buscar_drive_folder_id_trabajador(
        self,
        codigo_proyecto: str,
        nombre_trabajador: str,
    ) -> Optional[str]:
        """
        Busca el drive_folder_id en fct_acreditacion_solicitud_trabajador_manual.

        Args:
            codigo_proyecto: Codigo del proyecto
            nombre_trabajador: Nombre del trabajador

        Returns:
            drive_folder_id si se encuentra, None si no
        """
        try:
            response = (
                self.client.table("fct_acreditacion_solicitud_trabajador_manual")
                .select("drive_folder_id")
                .eq("codigo_proyecto", codigo_proyecto)
                .eq("nombre_trabajador", nombre_trabajador)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                drive_folder_id = response.data[0].get("drive_folder_id")
                logger.info(
                    "Encontrado drive_folder_id en trabajador: %s -> %s",
                    nombre_trabajador,
                    drive_folder_id,
                )
                return drive_folder_id

            logger.debug(
                "No se encontro drive_folder_id en trabajador para: %s, %s",
                codigo_proyecto,
                nombre_trabajador,
            )
            return None
        except Exception as e:
            logger.error(
                "Error buscando drive_folder_id en trabajador para %s: %s",
                nombre_trabajador,
                e,
            )
            return None

    def buscar_drive_folder_id_conductor(
        self,
        codigo_proyecto: str,
        nombre_trabajador: str,
    ) -> Optional[str]:
        """
        Busca el drive_folder_id en fct_acreditacion_solicitud_conductor_manual.

        Args:
            codigo_proyecto: Codigo del proyecto
            nombre_trabajador: Nombre del trabajador

        Returns:
            drive_folder_id si se encuentra, None si no
        """
        try:
            response = (
                self.client.table("fct_acreditacion_solicitud_conductor_manual")
                .select("drive_folder_id")
                .eq("codigo_proyecto", codigo_proyecto)
                .eq("nombre_trabajador", nombre_trabajador)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                drive_folder_id = response.data[0].get("drive_folder_id")
                logger.info(
                    "Encontrado drive_folder_id en conductor: %s -> %s",
                    nombre_trabajador,
                    drive_folder_id,
                )
                return drive_folder_id

            logger.debug(
                "No se encontro drive_folder_id en conductor para: %s, %s",
                codigo_proyecto,
                nombre_trabajador,
            )
            return None
        except Exception as e:
            logger.error(
                "Error buscando drive_folder_id en conductor para %s: %s",
                nombre_trabajador,
                e,
            )
            return None

    def buscar_drive_folder_id_vehiculo(
        self,
        id_proyecto: int,
        patente_vehiculo: str,
    ) -> Optional[str]:
        """
        Busca el drive_folder_id en fct_acreditacion_solicitud_vehiculos.

        Args:
            id_proyecto: ID del proyecto
            patente_vehiculo: Patente del vehiculo

        Returns:
            drive_folder_id si se encuentra, None si no
        """
        patente_normalizada = patente_vehiculo.strip()
        try:
            response = (
                self.client.table("fct_acreditacion_solicitud_vehiculos")
                .select("drive_folder_id")
                .eq("id_proyecto", id_proyecto)
                .eq("patente", patente_normalizada)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                drive_folder_id = response.data[0].get("drive_folder_id")
                logger.info(
                    "Encontrado drive_folder_id en vehiculo: proyecto=%s patente=%s -> %s",
                    id_proyecto,
                    patente_normalizada,
                    drive_folder_id,
                )
                return drive_folder_id

            logger.debug(
                "No se encontro drive_folder_id en vehiculo para: proyecto=%s patente=%s",
                id_proyecto,
                patente_normalizada,
            )
            return None
        except Exception as e:
            logger.error(
                "Error buscando drive_folder_id en vehiculo para proyecto=%s patente=%s: %s",
                id_proyecto,
                patente_normalizada,
                e,
            )
            return None

    def actualizar_brg_acreditacion_solicitud_requerimiento(
        self,
        registro_id: int,
        drive_folder_id: Optional[str] = None,
        parent_drive_id: Optional[str] = None,
    ) -> bool:
        """
        Actualiza columnas de Drive en brg_acreditacion_solicitud_requerimiento.

        Args:
            registro_id: ID del registro a actualizar
            drive_folder_id: Drive folder ID a asignar
            parent_drive_id: Parent folder ID anual (Shared Drive Proyectos YYYY)

        Returns:
            True si se actualizo exitosamente, False si no
        """
        update_payload: Dict[str, Any] = {}
        if drive_folder_id is not None:
            update_payload["drive_folder_id"] = drive_folder_id
        if parent_drive_id is not None:
            update_payload["parent_drive_id"] = parent_drive_id

        if not update_payload:
            logger.warning(
                "No hay columnas para actualizar en registro %s (payload vacio)",
                registro_id,
            )
            return False

        try:
            response = (
                self.client.table("brg_acreditacion_solicitud_requerimiento")
                .update(update_payload)
                .eq("id", registro_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(
                    "Actualizado registro %s con payload=%s",
                    registro_id,
                    update_payload,
                )
                return True

            logger.warning(
                "No se encontro registro con id %s para actualizar",
                registro_id,
            )
            return False
        except Exception as e:
            logger.error(
                "Error actualizando registro %s con payload=%s: %s",
                registro_id,
                update_payload,
                e,
            )
            return False


# Instancia global del servicio
supabase_service = SupabaseService()
