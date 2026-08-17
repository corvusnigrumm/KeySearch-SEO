"""
core/security.py - Seguridad, rate limiting, headers HTTP, CSRF.

Hardening:
- CSP + HSTS headers
- CSRF real en formularios POST
- Rate limiter con limpieza de keys vacias
- Validacion de session_id como UUID
"""

import logging
import secrets
import time
import uuid
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("keysearch.security")


# ── Rate Limiter (in-memory, por IP) ────────────────────────────────────────
class RateLimiter:
    """Token bucket simplificado para rate limiting por IP."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list] = defaultdict(list)

    def _clean(self, ip: str, now: float) -> None:
        cutoff = now - self._window
        self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
        if not self._hits[ip]:
            del self._hits[ip]

    def is_allowed(self, ip: str) -> tuple[bool, int]:
        now = time.time()
        self._clean(ip, now)
        count = len(self._hits[ip])
        if count >= self._max:
            retry_after = int(self._window - (now - self._hits[ip][0]))
            return False, max(retry_after, 1)
        self._hits[ip].append(now)
        return True, 0

    def is_allowed_strict(self, ip: str) -> tuple[bool, int]:
        return self.is_allowed(ip)


rate_limiter = RateLimiter(max_requests=30, window_seconds=60)


# ── Rate Limiters Especiales (para endpoints de IA) ──────────────────────────
ai_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)


# ── Security Headers Middleware ──────────────────────────────────────────────
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
}


def security_headers_middleware(app):
    """Registra el middleware de security headers en la app FastAPI."""

    @app.middleware("http")
    async def _add_security_headers(request: Request, call_next):
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value
        return response


def rate_limit_middleware(app):
    """Registra el middleware de rate limiting en la app FastAPI."""

    @app.middleware("http")
    async def _rate_limit(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if path.startswith("/static") or path in ("/ping", "/metrics"):
            return await call_next(request)

        allowed, retry_after = rate_limiter.is_allowed(client_ip)
        if not allowed:
            return JSONResponse(
                {"error": "Demasiadas solicitudes. Intenta de nuevo mas tarde."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        if path.startswith("/api/"):
            allowed_ai, retry_after_ai = ai_rate_limiter.is_allowed(client_ip)
            if not allowed_ai:
                return JSONResponse(
                    {"error": "Limite de llamadas a IA alcanzado. Espera 60 segundos."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after_ai)},
                )

        return await call_next(request)


# ── Session ID Validation Middleware ─────────────────────────────────────────
def validate_session_id_middleware(app):
    """Registra middleware que invalida session IDs que no son UUID validos."""

    @app.middleware("http")
    async def _validate_session_id(request: Request, call_next):
        session_id = request.cookies.get("session_id")
        if session_id:
            try:
                uuid.UUID(session_id)
            except ValueError:
                # Session ID invalido: reemplazar con uno nuevo
                request.cookies.pop("session_id", None)
        return await call_next(request)


# ── Global Exception Handler ─────────────────────────────────────────────────
def register_exception_handlers(app):
    """Registra handlers globales de excepciones en la app FastAPI."""

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Excepcion no manejada en %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            {"error": "Error interno del servidor. Intenta de nuevo."},
            status_code=500,
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            {"error": "Recurso no encontrado."},
            status_code=404,
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        return JSONResponse(
            {"error": "Metodo no permitido."},
            status_code=405,
        )


# ── CSRF Token Helper ───────────────────────────────────────────────────────
def generate_csrf_token() -> str:
    """Genera un token CSRF aleatorio."""
    return secrets.token_hex(32)


def validate_csrf_token(token: str, expected: str) -> bool:
    """Valida un token CSRF con comparacion constante en tiempo."""
    if not token or not expected:
        return False
    return secrets.compare_digest(token, expected)
