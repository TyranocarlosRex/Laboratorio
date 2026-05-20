from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import jwt_expires_minutes, jwt_secret_key

JWT_ALGORITHM = "HS256"

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    if _is_legacy_sha256_hash(stored_hash):
        return hmac.compare_digest(_legacy_sha256(password), stored_hash)

    try:
        return _password_hasher.verify(stored_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(stored_hash: str) -> bool:
    if _is_legacy_sha256_hash(stored_hash):
        return True

    try:
        return _password_hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return True


def create_access_token(usuario: Mapping[str, Any]) -> tuple[str, int]:
    expires_minutes = jwt_expires_minutes()
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=expires_minutes)

    payload = {
        "sub": str(usuario["id"]),
        "nombre": usuario["nombre"],
        "rol": usuario["rol"],
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(payload, jwt_secret_key(), algorithm=JWT_ALGORITHM)
    return token, expires_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, jwt_secret_key(), algorithms=[JWT_ALGORITHM])


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _is_legacy_sha256_hash(stored_hash: str) -> bool:
    return len(stored_hash) == 64 and all(
        character in "0123456789abcdef" for character in stored_hash.lower()
    )
