"""Configuracion de la aplicacion."""
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_secret(value: str, file_path: str, name: str) -> str:
    """Resolve a secret from an explicit value or a mounted secret file."""
    direct_value = value.strip()
    if direct_value:
        return direct_value

    configured_path = file_path.strip()
    if not configured_path:
        return ""

    path = Path(configured_path)
    try:
        secret = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"No se pudo leer {name} desde {path}") from exc

    if not secret:
        raise ValueError(f"El archivo configurado para {name} esta vacio: {path}")
    return secret


class Settings(BaseSettings):
    """Configuracion de la aplicacion desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Google Drive configuration
    GOOGLE_CLIENT_SECRET_FILE: str = "client_secret.json"
    GOOGLE_TOKEN_FILE: str = "token.json"

    # Supabase configuration
    SUPABASE_PROJECT_ID: str
    SUPABASE_URL: str
    SUPABASE_KEY: str = ""
    SUPABASE_KEY_FILE: str = ""

    # Internal API authentication
    ASIGNAR_FOLDER_API_TOKEN: str = ""
    ASIGNAR_FOLDER_API_TOKEN_FILE: str = ""

    # Application configuration
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "https://myma-acreditacion.onrender.com,http://localhost:3000,http://127.0.0.1:3000"

    @model_validator(mode="after")
    def resolve_runtime_secrets(self):
        """Load mounted secrets and fail closed in production."""
        self.SUPABASE_KEY = _resolve_secret(
            self.SUPABASE_KEY,
            self.SUPABASE_KEY_FILE,
            "SUPABASE_KEY",
        )
        if not self.SUPABASE_KEY:
            raise ValueError("SUPABASE_KEY o SUPABASE_KEY_FILE es obligatorio")

        self.ASIGNAR_FOLDER_API_TOKEN = _resolve_secret(
            self.ASIGNAR_FOLDER_API_TOKEN,
            self.ASIGNAR_FOLDER_API_TOKEN_FILE,
            "ASIGNAR_FOLDER_API_TOKEN",
        )
        if (
            self.ENVIRONMENT.strip().lower() == "production"
            and not self.ASIGNAR_FOLDER_API_TOKEN
        ):
            raise ValueError(
                "ASIGNAR_FOLDER_API_TOKEN o ASIGNAR_FOLDER_API_TOKEN_FILE "
                "es obligatorio en produccion"
            )
        return self


# Global settings instance
settings = Settings()
