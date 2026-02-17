"""Aplicación principal FastAPI."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routers import asignar_folder
from app.config import settings

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="API Asignar Folder ID a Requerimiento",
    description="API para asignar drive_folder_id a registros en brg_acreditacion_solicitud_requerimiento",
    version="1.0.0"
)

# CORS para frontend local y entornos configurados por variable de entorno.
allowed_origins = [
    origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(asignar_folder.router)


@app.get("/")
async def root():
    """Endpoint raíz con información de la API."""
    return JSONResponse(content={
        "nombre": "API Asignar Folder ID a Requerimiento",
        "version": "1.0.0",
        "descripcion": "API para asignar drive_folder_id a registros en brg_acreditacion_solicitud_requerimiento",
        "endpoints": {
            "asignar_folder": "/asignar-folder",
            "docs": "/docs",
            "health": "/health"
        }
    })


@app.get("/health")
async def health():
    """Endpoint de health check."""
    return JSONResponse(content={
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

