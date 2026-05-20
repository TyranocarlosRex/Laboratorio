from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal deploys
    load_dotenv = None


if load_dotenv:
    load_dotenv()


DEFAULT_ALLOWED_ORIGINS = ["*"]
DEFAULT_JWT_EXPIRES_MINUTES = 60


def database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "DATABASE_URL es obligatorio. Configura la cadena de conexion PostgreSQL."
        )
    return value


def jwt_secret_key() -> str:
    value = os.getenv("JWT_SECRET_KEY", "").strip()
    if not value:
        raise RuntimeError("JWT_SECRET_KEY es obligatorio para autenticacion.")
    return value


def jwt_expires_minutes() -> int:
    raw_minutes = os.getenv("JWT_EXPIRES_MINUTES", str(DEFAULT_JWT_EXPIRES_MINUTES))
    try:
        minutes = int(raw_minutes)
    except ValueError as error:
        raise RuntimeError("JWT_EXPIRES_MINUTES debe ser un numero entero.") from error

    if minutes <= 0:
        raise RuntimeError("JWT_EXPIRES_MINUTES debe ser mayor que cero.")

    return minutes


def allowed_origins() -> list[str]:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    if not raw_origins:
        return DEFAULT_ALLOWED_ORIGINS

    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or DEFAULT_ALLOWED_ORIGINS


def check_runtime_config() -> None:
    database_url()
    jwt_secret_key()
    jwt_expires_minutes()
    allowed_origins()
