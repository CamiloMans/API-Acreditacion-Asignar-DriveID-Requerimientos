# API Asignar Folder ID a Requerimiento

API FastAPI para asignar `drive_folder_id` en `brg_acreditacion_solicitud_requerimiento`.

## Resumen

La API procesa registros por `codigo_proyecto` y aplica estas reglas:

1. Si `categoria_requerimiento == "Empresa"`:
   - Si `empresa_acreditacion == "Myma"`: usa la carpeta `02 MYMA`.
   - Si es otra empresa: busca `01 Externos` y luego la carpeta con el nombre de la empresa.
   - Base de ruta:
     `Proyectos YYYY -> MY-XXX-YYYY -> 08 Terrenos -> 03 Acreditación y Arranque -> 01 Acreditación`.
2. Si `categoria_requerimiento != "Empresa"`:
   - Mantiene la logica anterior:
     - busca `drive_folder_id` en `fct_acreditacion_solicitud_trabajador_manual`
     - luego en `fct_acreditacion_solicitud_conductor_manual`
3. Si encuentra `drive_folder_id`, actualiza `brg_acreditacion_solicitud_requerimiento`.
4. Si no encuentra, continua con el siguiente registro.

Notas de matching:
- Comparaciones de categoria y empresa: `trim + case-insensitive`.
- Busqueda de carpetas en Drive: primero exacta, luego por `contains`.
- Este flujo no crea carpetas nuevas en Drive.

## Requisitos

- Python 3.11
- Variables de entorno en `.env`:

```env
# Google Drive
GOOGLE_CLIENT_SECRET_FILE=client_secret.json
GOOGLE_TOKEN_FILE=token.json

# Supabase
SUPABASE_PROJECT_ID=...
SUPABASE_URL=...
SUPABASE_KEY=...

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Ejecutar local

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Endpoint principal

### `POST /asignar-folder`

#### Request

```json
{
  "codigo_proyecto": "MY-000-2026",
  "registros": [
    {
      "id": 1,
      "categoria_requerimiento": "Empresa",
      "empresa_acreditacion": "Myma",
      "nombre_trabajador": "Alan Flores"
    },
    {
      "id": 2,
      "categoria_requerimiento": "Empresa",
      "empresa_acreditacion": "AGQ",
      "nombre_trabajador": "Pedro Diaz"
    },
    {
      "id": 3,
      "categoria_requerimiento": "Persona",
      "empresa_acreditacion": "AGQ",
      "nombre_trabajador": "Diego Soto"
    }
  ]
}
```

#### Response (ejemplo)

```json
{
  "codigo_proyecto": "MY-000-2026",
  "registros": [
    {
      "id": 1,
      "nombre_trabajador": "Alan Flores",
      "drive_folder_id_trabajador": null,
      "drive_folder_id_conductor": null,
      "drive_folder_id_final": "1abc...",
      "actualizado": true
    },
    {
      "id": 2,
      "nombre_trabajador": "Pedro Diaz",
      "drive_folder_id_trabajador": null,
      "drive_folder_id_conductor": null,
      "drive_folder_id_final": "1def...",
      "actualizado": true
    },
    {
      "id": 3,
      "nombre_trabajador": "Diego Soto",
      "drive_folder_id_trabajador": "1xyz...",
      "drive_folder_id_conductor": null,
      "drive_folder_id_final": "1xyz...",
      "actualizado": true
    }
  ],
  "resumen": {
    "total_registros": 3,
    "actualizados_exitosos": 3,
    "actualizados_fallidos": 0,
    "sin_drive_folder_id": 0
  },
  "mensaje": "Todos los registros fueron actualizados exitosamente"
}
```

## Logging

Se registran:
- categoria y empresa por registro
- origen del ID (`drive_empresa`, `supabase_trabajador`, `supabase_conductor`)
- casos donde no se encuentra carpeta o `drive_folder_id`

## Estructura

```text
app/
  main.py
  config.py
  models.py
  routers/
    asignar_folder.py
  services/
    drive_service.py
    supabase_service.py
```
