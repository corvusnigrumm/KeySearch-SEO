"""
core/monitoring.py - Structured logging, Request IDs, Health Checks y Prometheus Metrics.

Proporciona:
- JSON structured logging con request_id contextual
- Request ID middleware (UUID por request)
- Health check endpoint con DB, cache, uptime
- Prometheus metrics: request count, latency histogram, active sessions, AI calls
"""
import time
import uuid
import json
import logging
import datetime
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ── Prometheus Metrics ───────────────────────────────────────────────────────
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

APP_INFO = Info("keysearch", "KeySearch V10 Ultra application metadata")
APP_INFO.info({"version": "10.0"})

REQUEST_COUNT = Counter(
    "keysearch_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "keysearch_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

ACTIVE_SESSIONS = Gauge(
    "keysearch_active_sessions",
    "Number of active pipeline sessions",
)

AI_CALLS_TOTAL = Counter(
    "keysearch_ai_calls_total",
    "Total AI API calls",
    ["model", "status"],
)

AI_CALL_LATENCY = Histogram(
    "keysearch_ai_call_duration_seconds",
    "AI API call latency in seconds",
    ["model"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

DB_OPERATIONS = Counter(
    "keysearch_db_operations_total",
    "Total database operations",
    ["operation", "status"],
)

CACHE_HITS = Counter(
    "keysearch_cache_hits_total",
    "Cache hit/miss count",
    ["result"],
)

PIPELINE_RUNS = Counter(
    "keysearch_pipeline_runs_total",
    "Total pipeline runs",
    ["status"],
)


# ── Structured JSON Formatter ────────────────────────────────────────────────
class StructuredFormatter(logging.Formatter):
    """Formatter que genera logs en formato JSON estructurado."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            log_data["request_id"] = request_id

        client_ip = getattr(record, "client_ip", None)
        if client_ip:
            log_data["client_ip"] = client_ip

        method = getattr(record, "method", None)
        if method:
            log_data["method"] = method
            log_data["path"] = getattr(record, "path", "")

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log_data["duration_ms"] = round(duration_ms, 2)

        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            log_data["status_code"] = status_code

        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_structured_logging():
    """Configura logging estructurado JSON para la app."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root.handlers = [handler]

    for noisy in ("urllib3", "httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Request ID Middleware ────────────────────────────────────────────────────
_request_id_ctx: Dict[str, str] = {}


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware que asigna un UUID único a cada request y lo propaga al contexto de logging."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        _request_id_ctx["current"] = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        logger = logging.getLogger("keysearch.access")
        extra = {
            "request_id": request_id,
            "client_ip": request.client.host if request.client else "unknown",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        logger.info(
            "%s %s -> %s (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra=extra,
        )

        return response


def get_current_request_id() -> Optional[str]:
    return _request_id_ctx.get("current")


# ── Prometheus Middleware ─────────────────────────────────────────────────────
class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware que registra metricas Prometheus por cada request HTTP."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path == "/metrics" or path.startswith("/static"):
            return await call_next(request)

        method = request.method
        endpoint = _normalize_path(path)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        status = str(response.status_code)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

        return response


def _normalize_path(path: str) -> str:
    """Normaliza paths dinamicos para evitar alta cardinalidad en metricas.
    /api/generate-schema -> /api/generate-schema
    /users/123 -> /users/{id}
    """
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized) if normalized else "/"


# ── Metrics Endpoint Helper ──────────────────────────────────────────────────
def metrics_response() -> Response:
    """Retorna el payload de Prometheus en formato text/plain."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def update_active_sessions(count: int) -> None:
    """Actualiza el gauge de sesiones activas."""
    ACTIVE_SESSIONS.set(count)


# ── Health Check ─────────────────────────────────────────────────────────────
_start_time = time.time()


def compute_uptime() -> float:
    return time.time() - _start_time


def health_check_data() -> Dict[str, Any]:
    """Genera el payload completo de health check."""
    from core.database import SessionLocal, User, SearchHistory, PipelineSession

    db_ok = False
    db_error = ""
    user_count = 0
    session_count = 0
    history_count = 0
    try:
        db = SessionLocal()
        try:
            user_count = db.query(User).count()
            session_count = db.query(PipelineSession).count()
            history_count = db.query(SearchHistory).count()
            db_ok = True
        finally:
            db.close()
    except Exception as e:
        db_error = str(e)

    import config
    api_configured = bool(getattr(config, "GROQ_API_KEY", ""))

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": "10.0",
        "uptime_seconds": round(compute_uptime(), 1),
        "db": {
            "connected": db_ok,
            "error": db_error or None,
            "users": user_count,
            "sessions": session_count,
            "history_items": history_count,
        },
        "ai_configured": api_configured,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }
