"""Funciones auxiliares para el procesamiento de datos."""


def obtener_nombre_elemento(elemento):
    """
    Extrae el nombre de un elemento, ya sea string o objeto con 'nombre'.
    Compatible con ambos formatos para mantener retrocompatibilidad.
    
    Args:
        elemento: Puede ser un string o un diccionario con 'nombre' (y opcionalmente 'id')
    
    Returns:
        El nombre como string
    """
    if isinstance(elemento, dict) and 'nombre' in elemento:
        return elemento['nombre']
    elif isinstance(elemento, str):
        return elemento
    else:
        return str(elemento)


def obtener_id_elemento(elemento):
    """
    Extrae el id de un elemento si está disponible.
    
    Args:
        elemento: Puede ser un string o un diccionario con 'id'
    
    Returns:
        El id si está disponible, None si no
    """
    if isinstance(elemento, dict) and 'id' in elemento:
        return elemento['id']
    return None

