"""Router para asignar folder ID a requerimiento."""
import logging
import time
from typing import Dict, Optional, Tuple

from fastapi import APIRouter

from app.models import (
    AsignarFolderRequest,
    AsignarFolderResponse,
    RegistroResponse,
    ResumenActualizacion,
    _is_categoria_vehiculo,
)
from app.services.drive_service import drive_service
from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/asignar-folder", tags=["asignar-folder"])


def _normalize(value: str) -> str:
    """Normaliza texto para comparaciones case-insensitive + trim."""
    return value.strip().lower()


def _es_categoria_vehiculo(value: str) -> bool:
    """Determina si una categoria corresponde al flujo de vehiculos."""
    return _is_categoria_vehiculo(value)


@router.post("", response_model=AsignarFolderResponse)
def asignar_folder(request: AsignarFolderRequest):
    """
    Asigna drive_folder_id a registros en brg_acreditacion_solicitud_requerimiento.

    Reglas:
    - categoria_requerimiento == Empresa:
      - empresa_acreditacion == Myma -> MYMA/01 Empresa
      - otra empresa -> Externos/<empresa>/01 Empresa
    - categoria_requerimiento != Empresa:
      - flujo Supabase prioriza trabajador, conductor y luego vehiculo
    """
    logger.info(
        "Procesando asignacion de folder para proyecto=%s registros=%s",
        request.codigo_proyecto,
        len(request.registros),
    )

    registros_procesados = []
    actualizados_exitosos = 0
    actualizados_fallidos = 0
    sin_drive_folder_id = 0
    started_at = time.perf_counter()

    parent_ctx = drive_service.resolve_parent_drive_context(request.codigo_proyecto)
    parent_drive_id = parent_ctx["parent_drive_id"] if parent_ctx else None
    if parent_drive_id:
        logger.info(
            "parent_drive_id resuelto para codigo_proyecto=%s: %s",
            request.codigo_proyecto,
            parent_drive_id,
        )
    else:
        logger.warning(
            "No se pudo resolver parent_drive_id para codigo_proyecto=%s",
            request.codigo_proyecto,
        )

    # Cache por request para evitar recalcular ruta del proyecto en cada registro Empresa.
    proyecto_drive_ctx = None
    proyecto_drive_resuelto = False
    empresa_folder_cache: Dict[str, Optional[str]] = {}
    trabajador_folder_cache: Dict[str, Optional[str]] = {}
    conductor_folder_cache: Dict[str, Optional[str]] = {}
    vehiculo_folder_cache: Dict[Tuple[int, str], Optional[str]] = {}

    for registro in request.registros:
        categoria = _normalize(registro.categoria_requerimiento)
        es_categoria_vehiculo = _es_categoria_vehiculo(registro.categoria_requerimiento)
        empresa = registro.empresa_acreditacion.strip()
        empresa_normalizada = _normalize(registro.empresa_acreditacion)

        logger.debug(
            "Procesando registro id=%s nombre='%s' categoria='%s' empresa='%s'",
            registro.id,
            registro.nombre_trabajador,
            registro.categoria_requerimiento,
            registro.empresa_acreditacion,
        )

        drive_folder_id_trabajador = None
        drive_folder_id_conductor = None
        drive_folder_id_vehiculo = None
        drive_folder_id_final = None
        id_source = None

        if categoria == "empresa":
            if not proyecto_drive_resuelto:
                proyecto_drive_ctx = drive_service.resolve_acreditacion_root(
                    request.codigo_proyecto,
                    parent_ctx=parent_ctx,
                )
                proyecto_drive_resuelto = True
                if proyecto_drive_ctx and not parent_drive_id:
                    # Recupera parent_drive_id cuando la primera resolucion anual falla
                    # pero la ruta de acreditacion se logra resolver despues.
                    parent_drive_id = proyecto_drive_ctx.get("drive_id")
                    if parent_drive_id:
                        logger.info(
                            "parent_drive_id recuperado desde resolve_acreditacion_root "
                            "para codigo_proyecto=%s: %s",
                            request.codigo_proyecto,
                            parent_drive_id,
                        )

            if not proyecto_drive_ctx:
                logger.warning(
                    "No se pudo resolver ruta base de acreditacion para codigo_proyecto=%s",
                    request.codigo_proyecto,
                )
            else:
                if empresa_normalizada in empresa_folder_cache:
                    drive_folder_id_final = empresa_folder_cache[empresa_normalizada]
                    if drive_folder_id_final:
                        id_source = "drive_empresa_cache"
                else:
                    drive_id = proyecto_drive_ctx["drive_id"]
                    id_carpeta_proyecto = proyecto_drive_ctx["id_carpeta_acreditacion"]

                    if empresa_normalizada == "myma":
                        carpeta_myma_id = drive_service.find_folder_exact_or_contains(
                            "MYMA",
                            id_carpeta_proyecto,
                            drive_id,
                        )
                        if not carpeta_myma_id:
                            logger.warning(
                                "No se encontro carpeta 'MYMA' para codigo_proyecto=%s",
                                request.codigo_proyecto,
                            )
                        else:
                            drive_folder_id_final = drive_service.find_folder_exact_or_contains(
                                "01 Empresa",
                                carpeta_myma_id,
                                drive_id,
                                ignore_numeric_prefix=True,
                            )
                            id_source = "drive_empresa"
                    else:
                        carpeta_externos_id = drive_service.find_folder_exact_or_contains(
                            "Externos",
                            id_carpeta_proyecto,
                            drive_id,
                        )

                        if not carpeta_externos_id:
                            logger.warning(
                                "No se encontro carpeta 'Externos' para codigo_proyecto=%s",
                                request.codigo_proyecto,
                            )
                        else:
                            carpeta_empresa_id = drive_service.find_folder_exact_or_contains(
                                empresa,
                                carpeta_externos_id,
                                drive_id,
                            )
                            if not carpeta_empresa_id:
                                logger.warning(
                                    "No se encontro carpeta de contratista '%s' en Externos para codigo_proyecto=%s",
                                    empresa,
                                    request.codigo_proyecto,
                                )
                            else:
                                drive_folder_id_final = drive_service.find_folder_exact_or_contains(
                                    "01 Empresa",
                                    carpeta_empresa_id,
                                    drive_id,
                                    ignore_numeric_prefix=True,
                                )
                                id_source = "drive_empresa"

                    empresa_folder_cache[empresa_normalizada] = drive_folder_id_final

                if not drive_folder_id_final:
                    logger.warning(
                        "No se encontro carpeta de empresa para registro id=%s empresa='%s'",
                        registro.id,
                        empresa,
                    )
        else:
            if es_categoria_vehiculo:
                patente_normalizada = (registro.patente_vehiculo or "").strip()
                vehiculo_cache_key = (request.id_proyecto, patente_normalizada)
                if vehiculo_cache_key in vehiculo_folder_cache:
                    drive_folder_id_vehiculo = vehiculo_folder_cache[vehiculo_cache_key]
                else:
                    drive_folder_id_vehiculo = (
                        supabase_service.buscar_drive_folder_id_vehiculo(
                            request.id_proyecto,
                            patente_normalizada,
                        )
                    )
                    vehiculo_folder_cache[vehiculo_cache_key] = drive_folder_id_vehiculo
                drive_folder_id_final = drive_folder_id_vehiculo
                if drive_folder_id_vehiculo:
                    id_source = "supabase_vehiculo"
            else:
                nombre_trabajador = registro.nombre_trabajador or ""
                nombre_cache_key = _normalize(nombre_trabajador)

                if nombre_cache_key in trabajador_folder_cache:
                    drive_folder_id_trabajador = trabajador_folder_cache[nombre_cache_key]
                else:
                    drive_folder_id_trabajador = (
                        supabase_service.buscar_drive_folder_id_trabajador(
                            request.codigo_proyecto,
                            nombre_trabajador,
                        )
                    )
                    trabajador_folder_cache[nombre_cache_key] = drive_folder_id_trabajador

                if nombre_cache_key in conductor_folder_cache:
                    drive_folder_id_conductor = conductor_folder_cache[nombre_cache_key]
                else:
                    drive_folder_id_conductor = (
                        supabase_service.buscar_drive_folder_id_conductor(
                            request.codigo_proyecto,
                            nombre_trabajador,
                        )
                    )
                    conductor_folder_cache[nombre_cache_key] = drive_folder_id_conductor

                drive_folder_id_final = (
                    drive_folder_id_trabajador or drive_folder_id_conductor
                )

                if drive_folder_id_trabajador:
                    id_source = "supabase_trabajador"
                elif drive_folder_id_conductor:
                    id_source = "supabase_conductor"

                if (
                    not drive_folder_id_final
                    and registro.patente_vehiculo
                    and request.id_proyecto is not None
                ):
                    patente_normalizada = registro.patente_vehiculo.strip()
                    vehiculo_cache_key = (request.id_proyecto, patente_normalizada)
                    if vehiculo_cache_key in vehiculo_folder_cache:
                        drive_folder_id_vehiculo = vehiculo_folder_cache[vehiculo_cache_key]
                    else:
                        drive_folder_id_vehiculo = (
                            supabase_service.buscar_drive_folder_id_vehiculo(
                                request.id_proyecto,
                                patente_normalizada,
                            )
                        )
                        vehiculo_folder_cache[vehiculo_cache_key] = drive_folder_id_vehiculo
                    if drive_folder_id_vehiculo:
                        drive_folder_id_final = drive_folder_id_vehiculo
                        id_source = "supabase_vehiculo"

        actualizado = False
        if drive_folder_id_final:
            actualizado = supabase_service.actualizar_brg_acreditacion_solicitud_requerimiento(
                registro.id,
                drive_folder_id=drive_folder_id_final,
                parent_drive_id=parent_drive_id,
            )

            if actualizado:
                actualizados_exitosos += 1
            else:
                actualizados_fallidos += 1
        else:
            sin_drive_folder_id += 1
            if parent_drive_id:
                parent_actualizado = (
                    supabase_service.actualizar_brg_acreditacion_solicitud_requerimiento(
                        registro.id,
                        parent_drive_id=parent_drive_id,
                    )
                )
                if not parent_actualizado:
                    logger.warning(
                        "No se pudo actualizar parent_drive_id para registro id=%s",
                        registro.id,
                    )

        if drive_folder_id_final:
            logger.info(
                "Registro id=%s actualizado=%s source=%s drive_folder_id=%s",
                registro.id,
                actualizado,
                id_source,
                drive_folder_id_final,
            )
        else:
            logger.warning(
                "Registro id=%s sin drive_folder_id categoria='%s' empresa='%s'",
                registro.id,
                registro.categoria_requerimiento,
                registro.empresa_acreditacion,
            )

        registro_response = RegistroResponse(
            id=registro.id,
            nombre_trabajador=registro.nombre_trabajador,
            drive_folder_id_trabajador=drive_folder_id_trabajador,
            drive_folder_id_conductor=drive_folder_id_conductor,
            drive_folder_id_vehiculo=drive_folder_id_vehiculo,
            drive_folder_id_final=drive_folder_id_final,
            actualizado=actualizado,
        )
        registros_procesados.append(registro_response)

    resumen = ResumenActualizacion(
        total_registros=len(request.registros),
        actualizados_exitosos=actualizados_exitosos,
        actualizados_fallidos=actualizados_fallidos,
        sin_drive_folder_id=sin_drive_folder_id,
    )

    if actualizados_exitosos == len(request.registros):
        mensaje = "Todos los registros fueron actualizados exitosamente"
    elif actualizados_exitosos > 0:
        mensaje = (
            f"Se actualizaron {actualizados_exitosos} de {len(request.registros)} registros"
        )
    elif sin_drive_folder_id > 0:
        mensaje = f"No se encontro drive_folder_id para {sin_drive_folder_id} registro(s)"
    else:
        mensaje = "No se pudo actualizar ningun registro"

    elapsed = time.perf_counter() - started_at
    logger.info(
        (
            "Proceso completado actualizados=%s fallidos=%s sin_drive_folder_id=%s "
            "duracion=%.2fs cache_empresas=%s cache_trabajadores=%s "
            "cache_conductores=%s cache_vehiculos=%s"
        ),
        actualizados_exitosos,
        actualizados_fallidos,
        sin_drive_folder_id,
        elapsed,
        len(empresa_folder_cache),
        len(trabajador_folder_cache),
        len(conductor_folder_cache),
        len(vehiculo_folder_cache),
    )

    return AsignarFolderResponse(
        codigo_proyecto=request.codigo_proyecto,
        parent_drive_id=parent_drive_id,
        registros=registros_procesados,
        resumen=resumen,
        mensaje=mensaje,
    )
