"""Servicio para interactuar con Supabase."""
import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Servicio para operaciones con Supabase."""
    
    def __init__(self):
        """Inicializa el cliente de Supabase."""
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info(f"Cliente Supabase inicializado para proyecto: {settings.SUPABASE_PROJECT_ID}")
    
    def buscar_drive_folder_id_trabajador(
        self, 
        codigo_proyecto: str, 
        nombre_trabajador: str
    ) -> Optional[str]:
        """
        Busca el drive_folder_id en fct_acreditacion_solicitud_trabajador_manual.
        
        Args:
            codigo_proyecto: Código del proyecto
            nombre_trabajador: Nombre del trabajador
            
        Returns:
            drive_folder_id si se encuentra, None si no
        """
        try:
            response = self.client.table("fct_acreditacion_solicitud_trabajador_manual")\
                .select("drive_folder_id")\
                .eq("codigo_proyecto", codigo_proyecto)\
                .eq("nombre_trabajador", nombre_trabajador)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                drive_folder_id = response.data[0].get("drive_folder_id")
                logger.info(
                    f"Encontrado drive_folder_id en trabajador: {nombre_trabajador} -> {drive_folder_id}"
                )
                return drive_folder_id
            else:
                logger.debug(
                    f"No se encontró drive_folder_id en trabajador para: {codigo_proyecto}, {nombre_trabajador}"
                )
                return None
        except Exception as e:
            logger.error(
                f"Error buscando drive_folder_id en trabajador para {nombre_trabajador}: {e}"
            )
            return None
    
    def buscar_drive_folder_id_conductor(
        self, 
        codigo_proyecto: str, 
        nombre_trabajador: str
    ) -> Optional[str]:
        """
        Busca el drive_folder_id en fct_acreditacion_solicitud_conductor_manual.
        
        Args:
            codigo_proyecto: Código del proyecto
            nombre_trabajador: Nombre del trabajador
            
        Returns:
            drive_folder_id si se encuentra, None si no
        """
        try:
            response = self.client.table("fct_acreditacion_solicitud_conductor_manual")\
                .select("drive_folder_id")\
                .eq("codigo_proyecto", codigo_proyecto)\
                .eq("nombre_trabajador", nombre_trabajador)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                drive_folder_id = response.data[0].get("drive_folder_id")
                logger.info(
                    f"Encontrado drive_folder_id en conductor: {nombre_trabajador} -> {drive_folder_id}"
                )
                return drive_folder_id
            else:
                logger.debug(
                    f"No se encontró drive_folder_id en conductor para: {codigo_proyecto}, {nombre_trabajador}"
                )
                return None
        except Exception as e:
            logger.error(
                f"Error buscando drive_folder_id en conductor para {nombre_trabajador}: {e}"
            )
            return None
    
    def actualizar_brg_acreditacion_solicitud_requerimiento(
        self, 
        registro_id: int, 
        drive_folder_id: str
    ) -> bool:
        """
        Actualiza el drive_folder_id en brg_acreditacion_solicitud_requerimiento.
        
        Args:
            registro_id: ID del registro a actualizar
            drive_folder_id: Drive folder ID a asignar
            
        Returns:
            True si se actualizó exitosamente, False si no
        """
        try:
            response = self.client.table("brg_acreditacion_solicitud_requerimiento")\
                .update({"drive_folder_id": drive_folder_id})\
                .eq("id", registro_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(
                    f"Actualizado registro {registro_id} con drive_folder_id: {drive_folder_id}"
                )
                return True
            else:
                logger.warning(
                    f"No se encontró registro con id {registro_id} para actualizar"
                )
                return False
        except Exception as e:
            logger.error(
                f"Error actualizando registro {registro_id} con drive_folder_id {drive_folder_id}: {e}"
            )
            return False


# Instancia global del servicio
supabase_service = SupabaseService()

