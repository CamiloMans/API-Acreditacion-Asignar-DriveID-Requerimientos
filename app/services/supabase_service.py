"""Servicio para interactuar con Supabase."""
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Servicio para interactuar con Supabase."""
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        self.supabase_url = supabase_url or settings.supabase_url
        self.supabase_key = supabase_key or settings.supabase_key
        self.supabase: Optional[Client] = None
        
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
    
    def actualizar_drive_folder_ids(self, json_final: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza los campos drive_folder_id en Supabase usando los valores del JSON final.
        
        Args:
            json_final: Diccionario con la estructura del JSON final (con id_folder en cada registro)
        
        Returns:
            Diccionario con el resumen de actualizaciones (exitosas y fallidas)
        """
        if not self.supabase:
            logger.warning("Supabase no está configurado. No se actualizarán los drive_folder_id.")
            return {
                'especialistas_myma': {'exitosos': 0, 'fallidos': 0, 'errores': []},
                'especialistas_externo': {'exitosos': 0, 'fallidos': 0, 'errores': []},
                'conductores_myma': {'exitosos': 0, 'fallidos': 0, 'errores': []},
                'conductores_externo': {'exitosos': 0, 'fallidos': 0, 'errores': []}
            }
        
        resultados = {
            'especialistas_myma': {'exitosos': 0, 'fallidos': 0, 'errores': []},
            'especialistas_externo': {'exitosos': 0, 'fallidos': 0, 'errores': []},
            'conductores_myma': {'exitosos': 0, 'fallidos': 0, 'errores': []},
            'conductores_externo': {'exitosos': 0, 'fallidos': 0, 'errores': []}
        }
        
        # Actualizar especialistas MYMA
        if 'myma' in json_final and 'especialistas' in json_final['myma']:
            for especialista in json_final['myma']['especialistas']:
                if 'id' in especialista and 'id_folder' in especialista:
                    try:
                        self.supabase.table('fct_acreditacion_solicitud_trabajador_manual')\
                            .update({'drive_folder_id': especialista['id_folder']})\
                            .eq('id', especialista['id'])\
                            .execute()
                        resultados['especialistas_myma']['exitosos'] += 1
                        logger.info(f"Actualizado especialista MYMA {especialista.get('nombre', 'N/A')} (ID: {especialista['id']})")
                    except Exception as e:
                        resultados['especialistas_myma']['fallidos'] += 1
                        resultados['especialistas_myma']['errores'].append({
                            'id': especialista['id'],
                            'nombre': especialista.get('nombre', 'N/A'),
                            'error': str(e)
                        })
                        logger.error(f"Error actualizando especialista MYMA {especialista.get('nombre', 'N/A')}: {e}")
        
        # Actualizar especialistas Externo
        if 'externo' in json_final and 'especialistas' in json_final['externo']:
            for especialista in json_final['externo']['especialistas']:
                if 'id' in especialista and 'id_folder' in especialista:
                    try:
                        self.supabase.table('fct_acreditacion_solicitud_trabajador_manual')\
                            .update({'drive_folder_id': especialista['id_folder']})\
                            .eq('id', especialista['id'])\
                            .execute()
                        resultados['especialistas_externo']['exitosos'] += 1
                        logger.info(f"Actualizado especialista Externo {especialista.get('nombre', 'N/A')} (ID: {especialista['id']})")
                    except Exception as e:
                        resultados['especialistas_externo']['fallidos'] += 1
                        resultados['especialistas_externo']['errores'].append({
                            'id': especialista['id'],
                            'nombre': especialista.get('nombre', 'N/A'),
                            'error': str(e)
                        })
                        logger.error(f"Error actualizando especialista Externo {especialista.get('nombre', 'N/A')}: {e}")
        
        # Actualizar conductores MYMA
        if 'myma' in json_final and 'conductores' in json_final['myma']:
            for conductor in json_final['myma']['conductores']:
                if 'id' in conductor and 'id_folder' in conductor:
                    try:
                        self.supabase.table('fct_acreditacion_solicitud_conductor_manual')\
                            .update({'drive_folder_id': conductor['id_folder']})\
                            .eq('id', conductor['id'])\
                            .execute()
                        resultados['conductores_myma']['exitosos'] += 1
                        logger.info(f"Actualizado conductor MYMA {conductor.get('nombre', 'N/A')} (ID: {conductor['id']})")
                    except Exception as e:
                        resultados['conductores_myma']['fallidos'] += 1
                        resultados['conductores_myma']['errores'].append({
                            'id': conductor['id'],
                            'nombre': conductor.get('nombre', 'N/A'),
                            'error': str(e)
                        })
                        logger.error(f"Error actualizando conductor MYMA {conductor.get('nombre', 'N/A')}: {e}")
        
        # Actualizar conductores Externo
        if 'externo' in json_final and 'conductores' in json_final['externo']:
            for conductor in json_final['externo']['conductores']:
                if 'id' in conductor and 'id_folder' in conductor:
                    try:
                        self.supabase.table('fct_acreditacion_solicitud_conductor_manual')\
                            .update({'drive_folder_id': conductor['id_folder']})\
                            .eq('id', conductor['id'])\
                            .execute()
                        resultados['conductores_externo']['exitosos'] += 1
                        logger.info(f"Actualizado conductor Externo {conductor.get('nombre', 'N/A')} (ID: {conductor['id']})")
                    except Exception as e:
                        resultados['conductores_externo']['fallidos'] += 1
                        resultados['conductores_externo']['errores'].append({
                            'id': conductor['id'],
                            'nombre': conductor.get('nombre', 'N/A'),
                            'error': str(e)
                        })
                        logger.error(f"Error actualizando conductor Externo {conductor.get('nombre', 'N/A')}: {e}")
        
        return resultados

