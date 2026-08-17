"""
core/auth.py - Autenticacion segura: bcrypt + JWT con claims.
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger("keysearch.auth")

# ── Configuracion JWT ────────────────────────────────────────────────────────
_SECRET_FROM_ENV = os.environ.get("JWT_SECRET", "").strip()
SECRET_KEY = _SECRET_FROM_ENV if _SECRET_FROM_ENV else secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias
JWT_ISSUER = "keysearch"
JWT_AUDIENCE = "keysearch"

if not _SECRET_FROM_ENV:
    logger.warning(
        "JWT_SECRET no definido. Se genero una clave aleatoria. "
        "Todos los tokens se invalidaran al reiniciar el servidor. "
        "Define JWT_SECRET en tu .env o variable de entorno."
    )


# ── Password Hashing (bcrypt, resistente a brute-force) ─────────────────────
def get_password_hash(password: str) -> str:
    """Genera un hash bcrypt con salt automatico."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    h = bcrypt.hashpw(password_bytes, salt)
    return h.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica la contrasena contra el hash bcrypt. Comparacion constante en tiempo."""
    try:
        result = bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
        return result
    except Exception:
        # Fallback para hashes SHA-256 legacy durante migracion
        return _verify_password_legacy(plain_password, hashed_password)


def _verify_password_legacy(plain_password: str, hashed_password: str) -> bool:
    """Verifica hashes SHA-256 legacy. Retirar despues de migrar todos los usuarios."""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
        h = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
        return hmac.compare_digest(h, stored_hash)
    except (ValueError, AttributeError):
        return False


# ── JWT Tokens ────────────────────────────────────────────────────────────────
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Crea un JWT con claims estandar (iss, aud, exp, iat, jti)."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "jti": secrets.token_hex(16),
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica y valida un JWT. Retorna None si es invalido."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
        return payload
    except JWTError:
        return None
