import hashlib

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)


def test_passwords_are_hashed_with_argon2() -> None:
    stored_hash = hash_password("clave-segura-123")

    assert stored_hash.startswith("$argon2")
    assert stored_hash != "clave-segura-123"
    assert verify_password("clave-segura-123", stored_hash)
    assert not verify_password("clave-incorrecta", stored_hash)


def test_legacy_sha256_passwords_verify_but_need_rehash() -> None:
    legacy_hash = hashlib.sha256("clave-segura-123".encode("utf-8")).hexdigest()

    assert verify_password("clave-segura-123", legacy_hash)
    assert password_needs_rehash(legacy_hash)


def test_access_token_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "clave-de-prueba-larga")
    monkeypatch.setenv("JWT_EXPIRES_MINUTES", "60")
    token, expires_in = create_access_token(
        {"id": 7, "nombre": "Admin", "rol": "administrador"}
    )

    payload = decode_access_token(token)

    assert expires_in == 3600
    assert payload["sub"] == "7"
    assert payload["nombre"] == "Admin"
    assert payload["rol"] == "administrador"
