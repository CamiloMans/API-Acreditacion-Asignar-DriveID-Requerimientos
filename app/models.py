"""Modelos Pydantic para request y response."""
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional


class RegistroRequest(BaseModel):
    """Modelo para un registro individual en el request."""
    id: int = Field(..., description="ID del registro en brg_acreditacion_solicitud_requerimiento")
    categoria_requerimiento: str = Field(..., description="Categoria del requerimiento")
    empresa_acreditacion: str = Field(..., description="Empresa de acreditacion")
    nombre_trabajador: Optional[str] = Field(
        None,
        description="Nombre del trabajador. Puede ser null cuando categoria_requerimiento es Empresa",
    )

    @model_validator(mode="after")
    def validar_nombre_trabajador_por_categoria(self):
        """Exige nombre_trabajador para categorias distintas de Empresa."""
        categoria = (self.categoria_requerimiento or "").strip().lower()

        if categoria != "empresa":
            if not self.nombre_trabajador or not self.nombre_trabajador.strip():
                raise ValueError(
                    "nombre_trabajador es obligatorio cuando categoria_requerimiento no es 'Empresa'"
                )
            self.nombre_trabajador = self.nombre_trabajador.strip()

        return self


class AsignarFolderRequest(BaseModel):
    """Modelo para el request de asignar folder ID."""
    codigo_proyecto: str = Field(..., description="Código del proyecto")
    registros: List[RegistroRequest] = Field(..., description="Lista de registros a procesar")


class RegistroResponse(BaseModel):
    """Modelo para un registro individual en el response."""
    id: int = Field(..., description="ID del registro")
    nombre_trabajador: Optional[str] = Field(None, description="Nombre del trabajador")
    drive_folder_id_trabajador: Optional[str] = Field(None, description="Drive folder ID encontrado en tabla trabajador")
    drive_folder_id_conductor: Optional[str] = Field(None, description="Drive folder ID encontrado en tabla conductor")
    drive_folder_id_final: Optional[str] = Field(None, description="Drive folder ID final (prioriza trabajador)")
    actualizado: bool = Field(False, description="Indica si se actualizó en brg_acreditacion_solicitud_requerimiento")


class ResumenActualizacion(BaseModel):
    """Resumen de las actualizaciones realizadas."""
    total_registros: int = Field(..., description="Total de registros procesados")
    actualizados_exitosos: int = Field(..., description="Registros actualizados exitosamente")
    actualizados_fallidos: int = Field(..., description="Registros que fallaron al actualizar")
    sin_drive_folder_id: int = Field(..., description="Registros sin drive_folder_id encontrado")


class AsignarFolderResponse(BaseModel):
    """Modelo para el response de asignar folder ID."""
    codigo_proyecto: str = Field(..., description="Código del proyecto")
    registros: List[RegistroResponse] = Field(..., description="Lista de registros procesados")
    resumen: ResumenActualizacion = Field(..., description="Resumen de actualizaciones")
    mensaje: str = Field(..., description="Mensaje del resultado")

