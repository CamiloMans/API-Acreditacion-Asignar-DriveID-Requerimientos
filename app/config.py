"""Configuracion de la aplicacion."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuracion de la aplicacion desde variables de entorno."""

    # Google Drive configuration
    GOOGLE_CLIENT_SECRET_FILE: str = "client_secret.json"
    GOOGLE_TOKEN_FILE: str = "token.json"

    # Supabase configuration
    SUPABASE_PROJECT_ID: str
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Application configuration
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "https://myma-acreditacion.onrender.com,http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra keys in .env


# Global settings instance
settings = Settings()
