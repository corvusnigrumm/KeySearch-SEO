import hashlib
import os
from datetime import datetime, timedelta
from jose import jwt, JWTError

# ── Configuracion JWT ─────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias

# ── Password Hashing (SHA-256 + salt, sin dependencia de passlib/bcrypt) ──────
def get_password_hash(password: str) -> str:
    """Genera un hash seguro con salt aleatorio."""
    salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${h}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica la contraseña contra el hash almacenado."""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
        h = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
        return h == stored_hash
    except ValueError:
        return False

# ── JWT Tokens ────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
