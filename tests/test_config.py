import pytest

from app.config import (
    allowed_origins,
    check_runtime_config,
    database_url,
    jwt_expires_minutes,
    jwt_secret_key,
)


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL es obligatorio"):
        database_url()


def test_jwt_secret_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY es obligatorio"):
        jwt_secret_key()


def test_jwt_expiration_must_be_positive_integer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_EXPIRES_MINUTES", "0")

    with pytest.raises(RuntimeError, match="mayor que cero"):
        jwt_expires_minutes()

    monkeypatch.setenv("JWT_EXPIRES_MINUTES", "abc")

    with pytest.raises(RuntimeError, match="numero entero"):
        jwt_expires_minutes()


def test_allowed_origins_supports_comma_separated_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://laboratorio.example.com, http://localhost:3000",
    )

    assert allowed_origins() == [
        "https://laboratorio.example.com",
        "http://localhost:3000",
    ]


def test_runtime_config_passes_with_required_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.com/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "clave-larga-de-prueba")
    monkeypatch.setenv("JWT_EXPIRES_MINUTES", "60")

    check_runtime_config()
