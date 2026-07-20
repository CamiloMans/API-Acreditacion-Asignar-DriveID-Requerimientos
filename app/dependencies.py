"""Shared FastAPI dependencies."""
from secrets import compare_digest

from fastapi import Header, HTTPException, status

from app.config import settings


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Require the configured bearer token for mutating API requests."""
    expected_token = settings.ASIGNAR_FOLDER_API_TOKEN
    if not expected_token:
        return

    received_token = ""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            received_token = token.strip()

    if not received_token or not compare_digest(received_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de API invalido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
