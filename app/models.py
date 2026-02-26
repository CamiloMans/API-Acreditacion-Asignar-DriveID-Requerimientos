"""Modelos Pydantic para request y response."""
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


CATEGORIAS_VEHICULO = {"vehiculo", "vehiculos", "vehículo", "vehículos"}


def _normalize_categoria(value: Optional[str]) -> str:
    """Normaliza categoria para comparaciones."""
    return (value or "").strip().lower()


def _is_categoria_vehiculo(value: Optional[str]) -> bool:
    """Determina si una categoria corresponde a vehiculos."""
    return _normalize_categoria(value) in CATEGORIAS_VEHICULO


class RegistroRequest(BaseModel):
    """Modelo para un registro individual en el request."""

    id: int = Field(
        ...,
        description="ID del registro en brg_acreditacion_solicitud_requerimiento",
    )
    categoria_requerimiento: str = Field(..., description="Categoria del requerimiento")
    empresa_acreditacion: str = Field(..., description="Empresa de acreditacion")
    nombre_trabajador: Optional[str] = Field(
        None,
        description=(
            "Nombre del trabajador. Puede ser null cuando "
            "categoria_requerimiento es Empresa o Vehiculo"
        ),
    )
    patente_vehiculo: Optional[str] = Field(
        None,
        description="Patente del vehiculo. Requerida para categorias de vehiculo",
    )

    @model_validator(mode="after")
    def validar_campos_por_categoria(self):
        """Valida campos requeridos segun categoria y normaliza strings."""
        categoria = _normalize_categoria(self.categoria_requerimiento)
        es_empresa = categoria == "empresa"
        es_vehiculo = _is_categoria_vehiculo(self.categoria_requerimiento)

        if self.nombre_trabajador is not None:
            nombre = self.nombre_trabajador.strip()
            self.nombre_trabajador = nombre or None

        if self.patente_vehiculo is not None:
            patente = self.patente_vehiculo.strip()
            self.patente_vehiculo = patente or None

        if es_vehiculo:
            if not self.patente_vehiculo:
                raise ValueError(
                    "patente_vehiculo es obligatoria cuando categoria_requerimiento es de vehiculo"
                )
            return self

        if not es_empresa and not self.nombre_trabajador:
            raise ValueError(
                "nombre_trabajador es obligatorio cuando categoria_requerimiento no es 'Empresa'"
            )

        return self


class AsignarFolderRequest(BaseModel):
    """Modelo para el request de asignar folder ID."""

    id_proyecto: Optional[int] = Field(
        None,
        gt=0,
        description=(
            "ID del proyecto. Requerido si hay registros de vehiculo o patente_vehiculo"
        ),
    )
    codigo_proyecto: str = Field(..., description="Codigo del proyecto")
    registros: List[RegistroRequest] = Field(..., description="Lista de registros a procesar")

    @model_validator(mode="after")
    def validar_id_proyecto_para_busqueda_vehiculo(self):
        """Exige id_proyecto cuando el payload requiere lookup de vehiculos."""
        requiere_id_proyecto = any(
            _is_categoria_vehiculo(registro.categoria_requerimiento)
            or bool(registro.patente_vehiculo)
            for registro in self.registros
        )
        if requiere_id_proyecto and self.id_proyecto is None:
            raise ValueError(
                "id_proyecto es obligatorio cuando existe categoria de vehiculo o patente_vehiculo en registros"
            )
        return self


class RegistroResponse(BaseModel):
    """Modelo para un registro individual en el response."""

    id: int = Field(..., description="ID del registro")
    nombre_trabajador: Optional[str] = Field(None, description="Nombre del trabajador")
    drive_folder_id_trabajador: Optional[str] = Field(
        None,
        description="Drive folder ID encontrado en tabla trabajador",
    )
    drive_folder_id_conductor: Optional[str] = Field(
        None,
        description="Drive folder ID encontrado en tabla conductor",
    )
    drive_folder_id_vehiculo: Optional[str] = Field(
        None,
        description="Drive folder ID encontrado en tabla vehiculo",
    )
    drive_folder_id_final: Optional[str] = Field(
        None,
        description="Drive folder ID final (prioriza trabajador, conductor, vehiculo)",
    )
    actualizado: bool = Field(
        False,
        description="Indica si se actualizo en brg_acreditacion_solicitud_requerimiento",
    )


class ResumenActualizacion(BaseModel):
    """Resumen de las actualizaciones realizadas."""

    total_registros: int = Field(..., description="Total de registros procesados")
    actualizados_exitosos: int = Field(
        ...,
        description="Registros actualizados exitosamente",
    )
    actualizados_fallidos: int = Field(..., description="Registros que fallaron al actualizar")
    sin_drive_folder_id: int = Field(
        ...,
        description="Registros sin drive_folder_id encontrado",
    )


class AsignarFolderResponse(BaseModel):
    """Modelo para el response de asignar folder ID."""

    codigo_proyecto: str = Field(..., description="Codigo del proyecto")
    parent_drive_id: Optional[str] = Field(
        None,
        description="ID del Shared Drive anual Proyectos YYYY",
    )
    registros: List[RegistroResponse] = Field(..., description="Lista de registros procesados")
    resumen: ResumenActualizacion = Field(..., description="Resumen de actualizaciones")
    mensaje: str = Field(..., description="Mensaje del resultado")
