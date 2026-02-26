# API Asignar Folder ID a Requerimiento

API FastAPI para asignar `drive_folder_id` y `parent_drive_id` en
`brg_acreditacion_solicitud_requerimiento`.

## Resumen

La API procesa registros por `codigo_proyecto` y aplica estas reglas:

1. Si `categoria_requerimiento == "Empresa"`:
   - Si `empresa_acreditacion == "Myma"`: usa la carpeta `02 MYMA`.
   - Si es otra empresa: busca `01 Externos` y luego la carpeta con el nombre de la empresa.
   - Base de ruta:
     `Proyectos YYYY -> MY-XXX-YYYY -> 08 Terrenos -> 03 Acreditación y Arranque -> 01 Acreditación`.
2. Si `categoria_requerimiento != "Empresa"`:
   - Si es categoria de vehiculo (`vehiculo`, `vehiculos`, `vehículo`, `vehículos`):
     - no exige `nombre_trabajador`
     - exige `patente_vehiculo`
     - busca `drive_folder_id` en `fct_acreditacion_solicitud_vehiculos` por `id_proyecto + patente`
   - Para otras categorias no Empresa:
     - busca `drive_folder_id` en `fct_acreditacion_solicitud_trabajador_manual`
     - luego en `fct_acreditacion_solicitud_conductor_manual`
     - luego en `fct_acreditacion_solicitud_vehiculos` si el registro incluye `patente_vehiculo`
3. Resuelve `parent_drive_id` una sola vez por request desde el Shared Drive anual
   `Proyectos YYYY` segun el `codigo_proyecto` (`MY-XXX-YYYY`) y lo reutiliza para
   todos los registros del payload.
4. Si encuentra `drive_folder_id`, actualiza `drive_folder_id` y `parent_drive_id`.
5. Si no encuentra `drive_folder_id`, continua con el siguiente registro y, cuando
   existe, igual persiste `parent_drive_id`.

Notas de matching:
- Comparaciones de categoria y empresa: `trim + case-insensitive`.
- Patente de vehiculo: `trim` + match exacto en Supabase (sin normalizar formato).
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
  "id_proyecto": 123,
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
      "nombre_trabajador": "Diego Soto",
      "patente_vehiculo": "XZ99AA"
    },
    {
      "id": 4,
      "categoria_requerimiento": "Vehículos",
      "empresa_acreditacion": "AGQ",
      "nombre_trabajador": null,
      "patente_vehiculo": "ABCD12"
    }
  ]
}
```

Notas del request:
- `id_proyecto` es obligatorio si existe al menos un registro de vehiculo o si algun registro incluye `patente_vehiculo`.
- `nombre_trabajador` es obligatorio para categorias distintas de `Empresa` y vehiculo.
- `patente_vehiculo` es obligatoria para categorias de vehiculo.

#### Response (ejemplo)

```json
{
  "codigo_proyecto": "MY-000-2026",
  "parent_drive_id": "1parent...",
  "registros": [
    {
      "id": 1,
      "nombre_trabajador": "Alan Flores",
      "drive_folder_id_trabajador": null,
      "drive_folder_id_conductor": null,
      "drive_folder_id_vehiculo": null,
      "drive_folder_id_final": "1abc...",
      "actualizado": true
    },
    {
      "id": 2,
      "nombre_trabajador": "Pedro Diaz",
      "drive_folder_id_trabajador": null,
      "drive_folder_id_conductor": null,
      "drive_folder_id_vehiculo": null,
      "drive_folder_id_final": "1def...",
      "actualizado": true
    },
    {
      "id": 3,
      "nombre_trabajador": "Diego Soto",
      "drive_folder_id_trabajador": "1xyz...",
      "drive_folder_id_conductor": null,
      "drive_folder_id_vehiculo": null,
      "drive_folder_id_final": "1xyz...",
      "actualizado": true
    },
    {
      "id": 4,
      "nombre_trabajador": null,
      "drive_folder_id_trabajador": null,
      "drive_folder_id_conductor": null,
      "drive_folder_id_vehiculo": "1veh...",
      "drive_folder_id_final": "1veh...",
      "actualizado": true
    }
  ],
  "resumen": {
    "total_registros": 4,
    "actualizados_exitosos": 4,
    "actualizados_fallidos": 0,
    "sin_drive_folder_id": 0
  },
  "mensaje": "Todos los registros fueron actualizados exitosamente"
}
```

## Logging

Se registran:
- categoria y empresa por registro
- `parent_drive_id` resuelto para el request (si aplica)
- origen del ID (`drive_empresa`, `supabase_trabajador`, `supabase_conductor`, `supabase_vehiculo`)
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
