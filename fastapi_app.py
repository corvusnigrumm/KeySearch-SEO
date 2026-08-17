"""
Key Search V 10.0 Ultra - FastAPI Web Server
============================================
Suite Profesional de SEO, Keyword Research, Content Briefs, Schema FAQ y Ads Copywriting.
"""

import os
import io
import re
import csv
import json
import html as html_mod
import asyncio
import logging
import datetime
import uuid
import secrets
import urllib.parse
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

# Cargar .env local si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request, Form, BackgroundTasks, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session
from core.database import init_db, get_db, User, SearchHistory, PipelineSession, SessionLocal

import config
from core.auth import verify_password, get_password_hash, create_access_token, decode_access_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("keysearch")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


# ── Keep-alive loop ───────────────────────────────────────────────────────────
async def _keepalive_loop():
    """Hace ping interno cada 10 minutos para mantener el servidor despierto."""
    import httpx
    await asyncio.sleep(60)
    while True:
        try:
            async with httpx.AsyncClient() as client:
                port = int(os.environ.get("PORT", 8001))
                await client.get(f"http://localhost:{port}/ping", timeout=10)
            logger.info("Keep-alive ping OK")
        except Exception as e:
            logger.debug("Keep-alive ping silenciado: %s", e)
        await asyncio.sleep(600)


# ── Lifespan (reemplaza on_event deprecated) ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(_keepalive_loop())
    yield
    task.cancel()


app = FastAPI(title="Key Search V 10.0 Ultra", version="10.0", lifespan=lifespan)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

from pydantic import BaseModel, Field

class SchemaRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=500)
    questions: list = Field(default_factory=list)
    country: str = Field(default="Colombia", max_length=100)

class AdsCopyRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=500)
    questions: list = Field(default_factory=list)
    intent: str = Field(default="Informativa / Comercial", max_length=100)
    country: str = Field(default="Colombia", max_length=100)

class GroqModelRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=200)


class SchemaResponse(BaseModel):
    meta_title: str = ""
    meta_description: str = ""
    slug_sugerido: str = ""
    faq_items: list = Field(default_factory=list)


class AdsCopyResponse(BaseModel):
    google_ads: dict = Field(default_factory=dict)
    social_ads: dict = Field(default_factory=dict)
    tiktok_reels_hooks: list = Field(default_factory=list)
    guion_video_30s: dict = Field(default_factory=dict)


class GroqModelResponse(BaseModel):
    status: str = "ok"
    current_model: str = ""


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    db: dict = Field(default_factory=dict)
    ai_configured: bool = False
    timestamp: str = ""


class ErrorResponse(BaseModel):
    error: str

from core.security import (
    security_headers_middleware,
    rate_limit_middleware,
    register_exception_handlers,
    ai_rate_limiter,
    generate_csrf_token,
    validate_csrf_token,
)

security_headers_middleware(app)
rate_limit_middleware(app)
register_exception_handlers(app)

from core.monitoring import RequestIDMiddleware, setup_structured_logging

app.add_middleware(RequestIDMiddleware)
setup_structured_logging()

from core.monitoring import PrometheusMiddleware
app.add_middleware(PrometheusMiddleware)


# ── Gzip Compression Middleware ──────────────────────────────────────────────
import gzip as _gzip

@app.middleware("http")
async def gzip_middleware(request: Request, call_next):
    response = await call_next(request)
    accept = request.headers.get("accept-encoding", "")
    if "gzip" in accept and hasattr(response, "body"):
        body = response.body
        if isinstance(body, (bytes, bytearray)) and len(body) > 500:
            compressed = _gzip.compress(body, compresslevel=5)
            if len(compressed) < len(body):
                from starlette.responses import Response
                return Response(
                    content=compressed,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
    return response


# ── LRU Cache for repeated queries ───────────────────────────────────────────
from functools import lru_cache

@lru_cache(maxsize=128)
def _cached_country_names() -> dict:
    return {c: c for c in ["Colombia", "Mexico", "España", "Argentina", "Chile", "Peru", "USA"]}

@app.get("/logo-dorado.png")
async def serve_logo_dorado():
    logo_root = os.path.join(BASE_DIR, "LOGO DORADO.png")
    if os.path.exists(logo_root):
        return FileResponse(logo_root, media_type="image/png")
    logo_static = os.path.join(BASE_DIR, "static", "logo_dorado.png")
    if os.path.exists(logo_static):
        return FileResponse(logo_static, media_type="image/png")
    return JSONResponse({"error": "Logo no encontrado"}, status_code=404)


# ── Estado de sesion (persistido en DB) ──────────────────────────────────────
class SessionState:
    """Wrapper sobre PipelineSession de DB con interfaz compatible."""

    def __init__(self, db_session: PipelineSession = None):
        self._db = db_session
        self.logs: List[Dict[str, str]] = []

    @property
    def keywords(self) -> List[str]:
        if self._db and self._db.keywords_json:
            try:
                return json.loads(self._db.keywords_json)
            except Exception:
                return []
        return []

    @keywords.setter
    def keywords(self, value: List[str]):
        if self._db:
            self._db.keywords_json = json.dumps(value, ensure_ascii=False)

    @property
    def is_running(self) -> bool:
        return self._db.is_running if self._db else False

    @is_running.setter
    def is_running(self, value: bool):
        if self._db:
            self._db.is_running = value

    @property
    def progress(self) -> int:
        return self._db.progress if self._db else 0

    @progress.setter
    def progress(self, value: int):
        if self._db:
            self._db.progress = value

    @property
    def status_msg(self) -> str:
        return self._db.status_msg if self._db else "Listo."

    @status_msg.setter
    def status_msg(self, value: str):
        if self._db:
            self._db.status_msg = value

    @property
    def last_run_data(self) -> Optional[List[dict]]:
        if self._db and self._db.last_run_data_json:
            try:
                return json.loads(self._db.last_run_data_json)
            except Exception:
                return None
        return None

    @last_run_data.setter
    def last_run_data(self, value):
        if self._db:
            self._db.last_run_data_json = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def error_msg(self) -> Optional[str]:
        return self._db.error_msg if self._db else None

    @error_msg.setter
    def error_msg(self, value):
        if self._db:
            self._db.error_msg = value

    @property
    def country(self) -> str:
        return self._db.country if self._db else "co"

    @country.setter
    def country(self, value: str):
        if self._db:
            self._db.country = value

    @property
    def profile(self) -> str:
        return self._db.profile if self._db else "normal"

    @profile.setter
    def profile(self, value: str):
        if self._db:
            self._db.profile = value

    @property
    def started_at(self) -> Optional[str]:
        if self._db and self._db.started_at:
            return self._db.started_at.strftime("%Y-%m-%d %H:%M:%S")
        return None

    @started_at.setter
    def started_at(self, value: str):
        if self._db:
            self._db.started_at = datetime.datetime.now()

    @property
    def finished_at(self) -> Optional[str]:
        if self._db and self._db.finished_at:
            return self._db.finished_at.strftime("%Y-%m-%d %H:%M:%S")
        return None

    @finished_at.setter
    def finished_at(self, value: str):
        if self._db:
            self._db.finished_at = datetime.datetime.now()

    @property
    def user_id(self) -> Optional[int]:
        return self._db.user_id if self._db else None

    @user_id.setter
    def user_id(self, value):
        if self._db:
            self._db.user_id = value

    def reset(self):
        if self._db:
            self._db.keywords_json = "[]"
            self._db.is_running = False
            self._db.progress = 0
            self._db.status_msg = "Listo. Ingresa keywords para comenzar."
            self._db.last_run_data_json = None
            self._db.error_msg = None
            self._db.country = "co"
            self._db.profile = "normal"
            self._db.started_at = None
            self._db.finished_at = None
        self.logs = []

    def add_log(self, level: str, message: str):
        entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "msg": message,
        }
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    is_new = False

    # Validar que session_id sea un UUID valido (prevenir session fixation)
    if session_id:
        try:
            uuid.UUID(session_id)
        except ValueError:
            session_id = None

    if not session_id:
        session_id = str(uuid.uuid4())
        is_new = True

    request.state.session_id = session_id

    # Buscar o crear sesion en DB
    db = SessionLocal()
    try:
        db_session = db.query(PipelineSession).filter(PipelineSession.session_id == session_id).first()
        if not db_session:
            db_session = PipelineSession(session_id=session_id)
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
        request.state.db_session = db_session
        request.state.db_session_obj = db
    except Exception as exc:
        logger.error("Error en session middleware: %s", exc)
        db.close()
        request.state.db_session = None
        request.state.db_session_obj = None

    response = await call_next(request)

    # Flush cambios a DB despues de la request
    try:
        if request.state.db_session_obj:
            request.state.db_session_obj.commit()
            request.state.db_session_obj.close()
    except Exception:
        pass

    if is_new:
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=86400 * 30,
            httponly=True,
            samesite="lax",
        )
    return response


def get_session(request: Request) -> SessionState:
    db_session = getattr(request.state, "db_session", None)
    return SessionState(db_session)


# ── Helpers de contexto e Identidad ──────────────────────────────────────────
def get_current_user(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None

def get_current_user_or_redirect(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user

def _get_google_ads_detail() -> dict:
    """Devuelve diagnostico detallado de Google Ads para la UI. Sin secretos expuestos."""
    from scraper.google_ads_metrics import get_google_ads_status, HAS_GOOGLE_ADS_LIB
    status = get_google_ads_status()
    yaml_path = getattr(config, "GOOGLE_ADS_CONFIG_PATH", "")
    yaml_vals = config.parse_yaml_simple(yaml_path) if yaml_path and os.path.exists(yaml_path) else {}
    customer_id = config.get_dynamic_google_ads_customer_id()
    return {
        "enabled": status.get("enabled", False),
        "reason": status.get("reason", ""),
        "lib_installed": HAS_GOOGLE_ADS_LIB,
        "yaml_exists": bool(yaml_path and os.path.exists(yaml_path)),
        "yaml_path": yaml_path,
        "customer_id": customer_id,
        "customer_id_file": getattr(config, "GOOGLE_ADS_CUSTOMER_ID_FILE", ""),
        "has_developer_token": bool(yaml_vals.get("developer_token", "")),
        "has_client_id": bool(yaml_vals.get("client_id", "")),
        "has_client_secret": bool(yaml_vals.get("client_secret", "")),
        "has_refresh_token": bool(yaml_vals.get("refresh_token", "")),
        "has_login_customer_id": bool(yaml_vals.get("login_customer_id", "")),
    }


def _base_ctx(request: Request, user: User = None) -> dict:
    """Contexto base para todos los templates."""
    gads = _get_google_ads_detail()
    from scraper.volume_estimator import HAS_PYTRENDS
    return {
        "state": get_session(request),
        "groq_active": bool(os.getenv("GROQ_API_KEY", "")),
        "groq_model": getattr(config, "GROQ_MODEL", "openai/gpt-oss-120b"),
        "groq_available_models": getattr(config, "GROQ_AVAILABLE_MODELS", []),
        "google_ads_active": gads["enabled"],
        "google_ads": gads,
        "current_user": user,
        "free_suite": {
            "google": True,
            "youtube": True,
            "amazon": True,
            "bing": True,
            "duckduckgo": True,
            "wikipedia": True,
            "trends": HAS_PYTRENDS,
            "groq": bool(os.getenv("GROQ_API_KEY", "")),
        },
        "ai_chain": {
            "openai_active": bool(os.getenv("OPENAI_API_KEY", "")),
            "level1": "ChatGPT (gpt-4o-mini)" if os.getenv("OPENAI_API_KEY", "") else "GPT-OSS 120B (Groq)",
            "level2": "Qwen QwQ 32B (Groq)",
            "level3": "Llama 3.3 70B (Groq)",
        },
    }


# ── Rutas Autenticación ───────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})


@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        username = username.strip()
        if not username or not password:
            return templates.TemplateResponse(
                request=request, name="login.html",
                context={"request": request, "error": "Usuario y contrasena requeridos.", "show_register": True}
            )
        if len(password) < 4:
            return templates.TemplateResponse(
                request=request, name="login.html",
                context={"request": request, "error": "La contrasena debe tener al menos 4 caracteres.", "show_register": True}
            )

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return templates.TemplateResponse(
                request=request, name="login.html",
                context={"request": request, "error": "El perfil ya existe. Intenta ingresar.", "show_register": True}
            )

        new_user = User(username=username, password_hash=get_password_hash(password))
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info("Nuevo usuario registrado: %s (id=%s)", username, new_user.id)

        token = create_access_token({"sub": str(new_user.id)})
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=os.environ.get("HTTPS", "").lower() in ("1", "true", "yes"),
            max_age=60 * 60 * 24 * 7,
        )
        return response

    except Exception as exc:
        logger.error("Error en /register: %s", exc)
        db.rollback()
        return templates.TemplateResponse(
            request=request, name="login.html",
            context={"request": request, "error": "Error al crear la cuenta. Intenta de nuevo.", "show_register": True}
        )


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        username = username.strip()
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                request=request, name="login.html",
                context={"request": request, "error": "Usuario o contrasena incorrectos."}
            )

        token = create_access_token({"sub": str(user.id)})
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=os.environ.get("HTTPS", "").lower() in ("1", "true", "yes"),
            max_age=60 * 60 * 24 * 7,
        )
        logger.info("Login exitoso: %s (id=%s)", user.username, user.id)
        return response

    except Exception as exc:
        logger.error("Error en /login: %s", exc)
        return templates.TemplateResponse(
            request=request, name="login.html",
            context={"request": request, "error": "Error al iniciar sesion. Intenta de nuevo."}
        )


@app.post("/api/logout")
async def logout(request: Request):
    # Eliminar la PipelineSession de DB para invalidar la sesion
    session_id = request.cookies.get("session_id")
    if session_id:
        try:
            db = SessionLocal()
            session = db.query(PipelineSession).filter(PipelineSession.session_id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
            db.close()
        except Exception as exc:
            logger.error("Error eliminando sesion en logout: %s", exc)

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token", samesite="lax")
    response.delete_cookie("session_id", samesite="lax")
    return response


# ── Rutas HTML ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="dashboard.html", context=_base_ctx(request, user))


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="input.html", context=_base_ctx(request, user))


@app.get("/scraping", response_class=HTMLResponse)
async def scraping_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="scraping.html", context=_base_ctx(request, user))


@app.get("/clusters", response_class=HTMLResponse)
async def clusters_redirect(request: Request):
    return RedirectResponse(url="/tags", status_code=301)


@app.get("/tags", response_class=HTMLResponse)
async def tags_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="tags.html", context=_base_ctx(request, user))


@app.get("/editorial", response_class=HTMLResponse)
async def editorial_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="editorial_studio.html", context=_base_ctx(request, user))


@app.get("/ia", response_class=HTMLResponse)
async def ia_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="ia.html", context=_base_ctx(request, user))



@app.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="export.html", context=_base_ctx(request, user))


@app.get("/api-status", response_class=HTMLResponse)
async def api_status_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="api_status.html", context=_base_ctx(request, user))


@app.get("/logs-view", response_class=HTMLResponse)
async def logs_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="logs.html", context=_base_ctx(request, user))


@app.get("/ping")
async def ping_endpoint():
    return {"status": "ok"}


@app.get("/health")
async def health_endpoint():
    from core.monitoring import health_check_data
    data = health_check_data()
    status_code = 200 if data["status"] == "healthy" else 503
    return JSONResponse(data, status_code=status_code)


@app.get("/metrics")
async def metrics_endpoint():
    from core.monitoring import metrics_response
    return metrics_response()


# ── API: Estado del pipeline ──────────────────────────────────────────────────
@app.get("/status")
async def get_status(request: Request, user: User = Depends(get_current_user_or_redirect)):
    user_state = get_session(request)
    return {
        "is_running": user_state.is_running,
        "progress": user_state.progress,
        "status_msg": user_state.status_msg,
        "keywords_count": len(user_state.keywords),
        "results_count": len(user_state.last_run_data) if user_state.last_run_data else 0,
        "error": user_state.error_msg,
        "started_at": user_state.started_at,
        "finished_at": user_state.finished_at,
    }


@app.get("/api/logs")
async def get_logs(request: Request, user: User = Depends(get_current_user_or_redirect)):
    user_state = get_session(request)
    return {"logs": user_state.logs}


# ── API: Iniciar pipeline ─────────────────────────────────────────────────────
@app.post("/run")
async def run_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    keywords: str = Form(...),
    country: str = Form("co"),
    profile: str = Form("normal"),
    user: User = Depends(get_current_user_or_redirect)
):
    user_state = get_session(request)
    if user_state.is_running:
        return JSONResponse(
            {"status": "error", "message": "Pipeline en ejecución. Espera que termine."},
            status_code=400,
        )

    kw_list = [k.strip() for k in keywords.replace(",", "\n").split("\n") if k.strip()]
    if not kw_list:
        return JSONResponse(
            {"status": "error", "message": "No ingresaste ninguna keyword."},
            status_code=400,
        )
    if len(kw_list) > 20:
        return JSONResponse(
            {"status": "error", "message": "Maximo 20 keywords por ejecucion."},
            status_code=400,
        )
    # Limitar longitud de cada keyword
    kw_list = [k[:200] for k in kw_list]

    user_state.reset()
    user_state.user_id = user.id
    user_state.keywords = kw_list
    user_state.country = country
    user_state.profile = profile
    user_state.is_running = True
    user_state.progress = 0
    user_state.status_msg = f"Iniciando pipeline para {len(kw_list)} keyword(s)..."
    user_state.started_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_state.add_log("INFO", f"Pipeline iniciado por {user.username}: {len(kw_list)} keywords | País: {country} | Perfil: {profile}")

    background_tasks.add_task(_run_pipeline_task, user_state, kw_list, country, profile)
    return JSONResponse({"status": "success", "message": "Pipeline iniciado."})


# ── Historial de Búsquedas ────────────────────────────────────────────────────
@app.get("/historial", response_class=HTMLResponse)
async def historial_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="historial.html", context=_base_ctx(request, user))

@app.get("/api/history")
async def api_history(user: User = Depends(get_current_user_or_redirect), db: Session = Depends(get_db)):
    searches = db.query(SearchHistory).filter(SearchHistory.user_id == user.id).order_by(SearchHistory.created_at.desc()).all()
    history_list = []
    for s in searches:
        history_list.append({
            "id": s.id,
            "keyword": s.keyword,
            "country": s.country,
            "profile": s.profile,
            "created_at": s.created_at.isoformat()
        })
    return {"history": history_list}

@app.post("/api/generate-schema")
async def api_generate_schema(body: SchemaRequest, user: User = Depends(get_current_user_or_redirect)):
    """Genera Meta Tags de Alto CTR y Schema JSON-LD (FAQPage) bajo demanda."""
    try:
        kw = body.keyword.strip()
        questions = body.questions
        country = body.country
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.ai_generator import generar_schema_y_meta_tags
        schema_data = generar_schema_y_meta_tags(kw, questions, pais=country)
        return JSONResponse(schema_data)
    except Exception as e:
        logger.error("Error generando schema: %s", e)
        return JSONResponse({"error": "Error generando schema. Intenta de nuevo."}, status_code=500)

@app.post("/api/generate-ads-copy")
async def api_generate_ads_copy(body: AdsCopyRequest, user: User = Depends(get_current_user_or_redirect)):
    """Genera Copies de Google Ads, Facebook Ads y Hooks para TikTok bajo demanda."""
    try:
        kw = body.keyword.strip()
        questions = body.questions
        intent = body.intent
        country = body.country
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.ai_generator import generar_copywriting_ads_y_hooks as generar_ads_copy
        ads_data = generar_ads_copy(kw, preguntas=questions, intencion=intent, pais=country)
        return JSONResponse(ads_data)
    except Exception as e:
        logger.error("Error generando ads copy: %s", e)
        return JSONResponse({"error": "Error generando ads copy. Intenta de nuevo."}, status_code=500)


# NOTE: /api/generate-brief eliminado — reemplazado por el Estudio Editorial & Notas (/editorial)

@app.post("/api/set-groq-model")
async def api_set_groq_model(body: GroqModelRequest, user: User = Depends(get_current_user_or_redirect)):
    """Cambia el modelo de Groq activo dinámicamente."""
    try:
        model_id = body.model.strip()
        if not model_id:
            return JSONResponse({"error": "Modelo requerido"}, status_code=400)

        import config
        allowed_models = [m["id"] for m in getattr(config, "GROQ_AVAILABLE_MODELS", [])]
        if allowed_models and model_id not in allowed_models:
            return JSONResponse({"error": "Modelo no permitido."}, status_code=400)
        config.GROQ_MODEL = model_id
        logger.info("Modelo de Groq actualizado dinámicamente a: %s", model_id)
        return JSONResponse({"status": "ok", "current_model": model_id})
    except Exception as e:
        logger.error("Error cambiando modelo Groq: %s", e)
        return JSONResponse({"error": "Error cambiando modelo."}, status_code=500)

@app.get("/api/tags-data")
async def api_tags_data(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Devuelve los mejores tags de la sesión activa pre-calculados por el pipeline."""
    user_state = get_session(request)
    if not user_state or not user_state.last_run_data:
        return JSONResponse({"data": [], "has_data": False})
    items = []
    for item in user_state.last_run_data:
        items.append({
            "keyword": item.get("keyword", ""),
            "category": item.get("category", ""),
            "suggestions": item.get("suggestions", []),
            "paa": item.get("paa", []),
            "related": item.get("related", []),
            "editorial_tags": item.get("editorial_tags", {}),
        })
    return JSONResponse({"data": items, "has_data": True})


@app.post("/api/tags/generate")
async def api_tags_generate(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Genera tags bajo demanda para una keyword directa (uso independiente)."""
    try:
        data = await request.json()
        kw = data.get("keyword", "").strip()
        country = data.get("country", "Colombia")
        suggestions = data.get("suggestions", [])
        paa = data.get("paa", [])
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)
        from scraper.editorial_ideator import obtener_tags_reales_google
        tags_data = obtener_tags_reales_google(kw, sugerencias=suggestions, preguntas_paa=paa, pais=country)
        return JSONResponse({"keyword": kw, "tags": tags_data, "has_data": bool(tags_data)})
    except Exception as e:
        logger.error("Error generando tags: %s", e)
        return JSONResponse({"error": "Error generando tags."}, status_code=500)


@app.get("/api/editorial-session-data")
async def api_editorial_session_data(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Devuelve los datos pre-generados por el Pipeline del Data Input para el Estudio Editorial."""
    user_state = get_session(request)
    if not user_state or not user_state.last_run_data:
        return JSONResponse({"data": [], "has_data": False})
    items = []
    for item in user_state.last_run_data:
        items.append({
            "keyword": item.get("keyword", ""),
            "category": item.get("category", ""),
            "suggestions": item.get("suggestions", []),
            "paa": item.get("paa", []),
            "related": item.get("related", []),
            "editorial_tags": item.get("editorial_tags"),
            "editorial_ideas": item.get("editorial_ideas"),
            "editorial_nota": item.get("editorial_nota"),
            "seo_schema": item.get("seo_schema"),
            "ads_copy": item.get("ads_copy"),
        })
    return JSONResponse({"data": items, "has_data": True})

# ── API Editorial: Ideas, Redacción y Tags Reales ────────────────────────────
@app.post("/api/editorial/tags-reales")
async def api_editorial_tags_reales(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Extrae tags 100% reales de Google Trends (Rising/Breakout, Top y Topics) y Google Suggest."""
    try:
        data = await request.json()
        kw = data.get("keyword", "").strip()
        suggestions = data.get("suggestions", [])
        paa = data.get("paa", [])
        country = data.get("country", "Colombia")
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.editorial_ideator import obtener_tags_reales_google
        tags_data = obtener_tags_reales_google(kw, sugerencias=suggestions, preguntas_paa=paa, pais=country)
        return JSONResponse(tags_data)
    except Exception as e:
        logger.error("Error obteniendo tags reales: %s", e)
        return JSONResponse({"error": "Error obteniendo tags reales."}, status_code=500)

@app.post("/api/editorial/idear")
async def api_editorial_idear(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Genera 5 ángulos e ideas de notas periodísticas siguiendo el manual de estilo."""
    try:
        data = await request.json()
        kw = data.get("keyword", "").strip()
        suggestions = data.get("suggestions", [])
        paa = data.get("paa", [])
        country = data.get("country", "Colombia")
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.editorial_ideator import obtener_tags_reales_google, generar_ideas_notas_angulos
        tags_data = data.get("tags_reales") or obtener_tags_reales_google(kw, sugerencias=suggestions, preguntas_paa=paa, pais=country)
        ideas = generar_ideas_notas_angulos(kw, sugerencias=suggestions, preguntas_paa=paa, pais=country, tags_reales=tags_data)
        return JSONResponse({"ideas": ideas, "tags_reales": tags_data})
    except Exception as e:
        logger.error("Error ideando notas editoriales: %s", e)
        return JSONResponse({"error": "Error generando ideas editoriales."}, status_code=500)

@app.post("/api/editorial/redactar")
async def api_editorial_redactar(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Redacta una nota periodística completa respetando la fórmula editorial de referencia."""
    try:
        data = await request.json()
        kw = data.get("keyword", "").strip()
        angulo = data.get("angulo", "Trucos y Hacks Cotidianos")
        titular_h1 = data.get("titular_h1")
        suggestions = data.get("suggestions", [])
        paa = data.get("paa", [])
        country = data.get("country", "Colombia")
        tags_reales = data.get("tags_reales")
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.editorial_ideator import redactar_nota_editorial
        nota = redactar_nota_editorial(
            keyword_base=kw,
            angulo=angulo,
            titular_h1=titular_h1,
            sugerencias=suggestions,
            preguntas_paa=paa,
            pais=country,
            tags_reales=tags_reales,
        )
        return JSONResponse(nota)
    except Exception as e:
        logger.error("Error redactando nota editorial: %s", e)
        return JSONResponse({"error": "Error redactando nota editorial."}, status_code=500)

@app.post("/api/editorial/exportar-docx")
async def api_editorial_exportar_docx(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Genera y descarga un archivo .docx profesional de la nota redactada."""
    try:
        data = await request.json()
        nota_data = data.get("nota_data", {})
        if not nota_data:
            return JSONResponse({"error": "Datos de nota requeridos"}, status_code=400)

        from scraper.editorial_ideator import exportar_nota_docx
        doc_stream = exportar_nota_docx(nota_data)
        
        # Nombre de archivo limpio (prevenir header injection)
        h1_raw = nota_data.get("titular_h1", "Nota_Editorial")
        clean_name = re.sub(r'[^\w\s-]', "", h1_raw).strip().replace(" ", "_")[:60]
        if not clean_name:
            clean_name = "Nota_Editorial"
        # Prevenir path traversal en filename
        clean_name = re.sub(r'\.\.', "", clean_name)
        filename = f"{clean_name}.docx"

        return StreamingResponse(
            doc_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error("Error exportando docx: %s", e)
        return JSONResponse({"error": "Error exportando documento."}, status_code=500)

@app.get("/download/history/{item_id}")
async def download_history_excel(item_id: int, user: User = Depends(get_current_user_or_redirect), db: Session = Depends(get_db)):
    search = db.query(SearchHistory).filter(SearchHistory.id == item_id, SearchHistory.user_id == user.id).first()
    if not search:
        return JSONResponse({"error": "Búsqueda no encontrada o no tienes permisos."}, status_code=404)
    
    try:
        from exporters.excel_export import exportar_excel
        item = json.loads(search.json_data)
        
        datos = {
            "volumenes": item.get("metrics", {}),
            "language_code": search.country.split("-")[0] if "-" in search.country else search.country,
            "sugerencias": item.get("suggestions", []),
            "preguntas_paa": item.get("paa", []),
            "preguntas_autocompletado": item.get("preguntas_autocompletado", []),
            "busquedas_relacionadas": item.get("related", []),
            "country_name": item.get("country_name", search.country.title()),
            "country_code": item.get("country_code", search.country.upper()),
            "category_name": item.get("category", ""),
            "subcategory_name": item.get("subcategory", ""),
            "google_ads": item.get("google_ads", {}),
            "editorial_tags": item.get("editorial_tags", {}),
            "editorial_ideas": item.get("editorial_ideas", []),
            "editorial_nota": item.get("editorial_nota", {}),
        }
        
        ruta_archivo = exportar_excel(search.keyword, datos)
        filename = os.path.basename(ruta_archivo)
        return FileResponse(
            ruta_archivo, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )
    except Exception as e:
        logger.exception("Error generando Excel histórico")
        return JSONResponse({"error": "Error generando Excel historico."}, status_code=500)


# ── Descarga de resultados ────────────────────────────────────────────────────
from fastapi.responses import FileResponse

@app.get("/download/excel")
async def download_excel(request: Request, user: User = Depends(get_current_user_or_redirect)):
    user_state = get_session(request)
    if not user_state.last_run_data:
        return JSONResponse({"error": "No hay datos para exportar. Ejecuta primero el pipeline."}, status_code=404)

    from exporters.excel_export import exportar_excel

    if len(user_state.last_run_data) == 1:
        item = user_state.last_run_data[0]
        datos = {
            "volumenes": item.get("metrics", {}),
            "language_code": user_state.country.split("-")[0] if "-" in user_state.country else user_state.country,
            "sugerencias": item.get("suggestions", []),
            "preguntas_paa": item.get("paa", []),
            "preguntas_autocompletado": item.get("preguntas_autocompletado", []),
            "busquedas_relacionadas": item.get("related", []),
            "country_name": item.get("country_name", user_state.country.title()),
            "country_code": item.get("country_code", user_state.country.upper()),
            "category_name": item.get("category", ""),
            "subcategory_name": item.get("subcategory", ""),
            "google_ads": item.get("google_ads", {}),
            "editorial_tags": item.get("editorial_tags", {}),
            "editorial_ideas": item.get("editorial_ideas", []),
            "editorial_nota": item.get("editorial_nota", {}),
        }
        try:
            ruta_archivo = exportar_excel(item["keyword"], datos)
            filename = os.path.basename(ruta_archivo)
            return FileResponse(
                ruta_archivo, 
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=filename
            )
        except Exception as e:
            logger.exception("Error generando Excel")
            return JSONResponse({"error": "Error generando Excel."}, status_code=500)
    else:
        # Modo Batch: generar un ZIP con un Excel por cada keyword
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for item in user_state.last_run_data:
                    kw = item["keyword"]
                    datos = {
                        "volumenes": item.get("metrics", {}),
                        "language_code": user_state.country.split("-")[0] if "-" in user_state.country else user_state.country,
                        "sugerencias": item.get("suggestions", []),
                        "preguntas_paa": item.get("paa", []),
                        "preguntas_autocompletado": item.get("preguntas_autocompletado", []),
                        "busquedas_relacionadas": item.get("related", []),
                        "country_name": item.get("country_name", ""),
                        "country_code": item.get("country_code", ""),
                        "category_name": item.get("category", ""),
                        "subcategory_name": item.get("subcategory", ""),
                        "google_ads": item.get("google_ads", {}),
                    }
                    ruta_archivo = exportar_excel(kw, datos)
                    filename = os.path.basename(ruta_archivo)
                    zip_file.write(ruta_archivo, arcname=filename)
            
            zip_buffer.seek(0)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename=resultados_lote_{timestamp}.zip"}
            )
        except Exception as e:
            logger.exception("Error generando ZIP de Excel")
            return JSONResponse({"error": "Error generando ZIP."}, status_code=500)



@app.get("/download/json")
async def download_json(request: Request, user: User = Depends(get_current_user_or_redirect)):
    user_state = get_session(request)
    if not user_state.last_run_data:
        return JSONResponse({"error": "No hay datos para exportar."}, status_code=404)

    data = {
        "meta": {
            "generated_at": user_state.finished_at or datetime.datetime.now().isoformat(),
            "country": user_state.country,
            "profile": user_state.profile,
            "total_keywords": len(user_state.last_run_data),
        },
        "results": user_state.last_run_data,
    }

    filename = f"keysearch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        iter([json.dumps(data, ensure_ascii=False, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Google Ads: Configuración, Test y OAuth ──────────────────────────────────
_oauth_states: Dict[str, dict] = {}  # state → {client_id, client_secret, redirect_uri}


@app.post("/api/config/google-ads")
async def save_google_ads_config(
    request: Request,
    developer_token: str = Form(""),
    client_id: str = Form(""),
    client_secret: str = Form(""),
    refresh_token: str = Form(""),
    login_customer_id: str = Form(""),
    customer_id: str = Form(""),
    user: User = Depends(get_current_user_or_redirect),
):
    """Guarda la configuracion de Google Ads en los archivos locales."""
    yaml_path = getattr(config, "GOOGLE_ADS_CONFIG_PATH", os.path.join(BASE_DIR, "google-ads.yaml"))
    cid_path = getattr(config, "GOOGLE_ADS_CUSTOMER_ID_FILE", os.path.join(BASE_DIR, "google-ads.customer-id.txt"))

    # Preservar valores existentes si el campo viene vacio
    existing = config.parse_yaml_simple(yaml_path) if os.path.exists(yaml_path) else {}

    def _sanitize_yaml_val(val: str) -> str:
        return re.sub(r'[\n\r"\\]', '', val).strip()[:500]

    final_dev = _sanitize_yaml_val(developer_token) if developer_token.strip() else _sanitize_yaml_val(existing.get("developer_token", ""))
    final_cid = _sanitize_yaml_val(client_id) if client_id.strip() else _sanitize_yaml_val(existing.get("client_id", ""))
    final_csec = _sanitize_yaml_val(client_secret) if client_secret.strip() else _sanitize_yaml_val(existing.get("client_secret", ""))
    final_refresh = _sanitize_yaml_val(refresh_token) if refresh_token.strip() else _sanitize_yaml_val(existing.get("refresh_token", ""))
    final_login = _sanitize_yaml_val(login_customer_id.replace("-", "")) if login_customer_id.strip() else _sanitize_yaml_val(existing.get("login_customer_id", ""))

    yaml_content = (
        f'developer_token: "{final_dev}"\n'
        f'client_id: "{final_cid}"\n'
        f'client_secret: "{final_csec}"\n'
        f'refresh_token: "{final_refresh}"\n'
        f'login_customer_id: "{final_login}"\n'
        f'use_proto_plus: true\n'
    )
    try:
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        clean_cid = re.sub(r'[^0-9]', '', customer_id)[:20]
        with open(cid_path, "w", encoding="utf-8") as f:
            f.write(clean_cid)
        logger.info("Google Ads config guardada por %s", user.username)
        return JSONResponse({"status": "ok", "message": "Configuracion de Google Ads guardada correctamente."})
    except Exception as exc:
        logger.exception("Error guardando config de Google Ads")
        return JSONResponse({"status": "error", "message": "Error guardando configuracion."}, status_code=500)


@app.post("/api/test/google-ads")
async def test_google_ads_connection(
    request: Request,
    user: User = Depends(get_current_user_or_redirect),
):
    """Ejecuta una prueba de conexión con Google Ads API."""
    loop = asyncio.get_event_loop()
    def _test():
        from scraper.google_ads_metrics import enrich_with_google_ads_metrics, get_google_ads_status
        status = get_google_ads_status()
        if not status.get("enabled"):
            return {"success": False, "detail": status.get("reason", "Google Ads no habilitado."), "status": status}
        metricas_prueba = {
            "marketing digital": {
                "score": 100.0, "categoria": "Test", "fuente": "Test",
                "posicion_fuente": 1, "fuentes": ["Test"],
                "google_ads_keyword_text": None, "google_ads_close_variants": [],
                "google_ads_avg_monthly_searches": None, "google_ads_competition": None,
                "google_ads_competition_index": None,
                "google_ads_low_top_of_page_bid_micros": None,
                "google_ads_high_top_of_page_bid_micros": None,
                "google_ads_monthly_search_volumes": [],
            }
        }
        result = enrich_with_google_ads_metrics(metricas_prueba)
        if result.get("enabled") and result.get("keywords_enriched", 0) > 0:
            vol = metricas_prueba["marketing digital"].get("google_ads_avg_monthly_searches")
            return {
                "success": True,
                "detail": f"Conexión exitosa. Volumen de prueba para 'marketing digital': {vol} búsquedas/mes.",
                "avg_monthly_searches": vol,
                "result": result,
            }
        else:
            return {
                "success": False,
                "detail": result.get("reason", "No se pudieron obtener métricas."),
                "result": result,
            }
    try:
        res = await loop.run_in_executor(None, _test)
        return JSONResponse(res)
    except Exception as exc:
        logger.exception("Error en test de Google Ads")
        return JSONResponse({"success": False, "detail": "Error inesperado en la prueba."}, status_code=500)


@app.get("/api/google-ads/auth")
async def google_ads_oauth_start(request: Request):
    """Inicia el flujo OAuth de Google para obtener un refresh token."""
    yaml_path = getattr(config, "GOOGLE_ADS_CONFIG_PATH", os.path.join(BASE_DIR, "google-ads.yaml"))
    vals = config.parse_yaml_simple(yaml_path)
    cid = vals.get("client_id", "")
    csecret = vals.get("client_secret", "")
    if not cid or not csecret:
        return JSONResponse({"error": "Primero guarda client_id y client_secret en la configuracion."}, status_code=400)

    state = secrets.token_urlsafe(24)
    # Usar redirect_uri fijo desde config para prevenir Host header injection
    base_url = os.environ.get("APP_BASE_URL", "http://localhost:8001").rstrip("/")
    redirect_uri = f"{base_url}/api/google-ads/callback"

    _oauth_states[state] = {"client_id": cid, "client_secret": csecret, "redirect_uri": redirect_uri}

    params = urllib.parse.urlencode({
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/adwords",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    return RedirectResponse(auth_url)


@app.get("/api/google-ads/callback")
async def google_ads_oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """Callback de OAuth. Intercambia el code por refresh_token y lo guarda."""
    if error:
        safe_error = html_mod.escape(error[:200])
        return HTMLResponse(f"<h2>Error de Google: {safe_error}</h2><p><a href='/api-status'>Volver</a></p>", status_code=400)
    if state not in _oauth_states:
        return HTMLResponse("<h2>Estado invalido o expirado.</h2><p><a href='/api-status'>Volver</a></p>", status_code=400)

    ctx = _oauth_states.pop(state)
    import requests as http_requests
    try:
        resp = http_requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": ctx["client_id"],
            "client_secret": ctx["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": ctx["redirect_uri"],
        }, timeout=30)
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as exc:
        logger.exception("Error intercambiando code por tokens")
        return HTMLResponse("<h2>Error obteniendo tokens. Reintenta el flujo.</h2><p><a href='/api-status'>Volver</a></p>", status_code=500)

    new_refresh = token_data.get("refresh_token", "")
    if not new_refresh:
        return HTMLResponse("<h2>No se recibio refresh_token. Reintenta el flujo.</h2><p><a href='/api-status'>Volver</a></p>", status_code=400)

    # Leer yaml actual y sobrescribir refresh_token
    yaml_path = getattr(config, "GOOGLE_ADS_CONFIG_PATH", os.path.join(BASE_DIR, "google-ads.yaml"))
    vals = config.parse_yaml_simple(yaml_path)

    def _sanitize_yaml_val(val: str) -> str:
        return re.sub(r'[\n\r"\\]', '', str(val)).strip()[:500]

    yaml_content = (
        f'developer_token: "{_sanitize_yaml_val(vals.get("developer_token", ""))}"\n'
        f'client_id: "{_sanitize_yaml_val(vals.get("client_id", ""))}"\n'
        f'client_secret: "{_sanitize_yaml_val(vals.get("client_secret", ""))}"\n'
        f'refresh_token: "{_sanitize_yaml_val(new_refresh)}"\n'
        f'login_customer_id: "{_sanitize_yaml_val(vals.get("login_customer_id", ""))}"\n'
        f'use_proto_plus: true\n'
    )
    try:
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
    except Exception as exc:
        logger.exception("Error guardando refresh_token")
        return HTMLResponse("<h2>Token obtenido pero hubo un error guardandolo.</h2>", status_code=500)

    logger.info("Refresh token de Google Ads obtenido y guardado exitosamente.")
    return RedirectResponse("/api-status?oauth=success")


# ── Tarea asíncrona del pipeline ──────────────────────────────────────────────
async def _run_pipeline_task(user_state: SessionState, keywords: List[str], country_code: str, profile: str):
    try:
        user_state.add_log("INFO", "Cargando modulos del motor de scraping...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _blocking_pipeline, user_state, keywords, country_code, profile
        )
        user_state.last_run_data = result
        user_state.status_msg = f"Completado. {len(result)} keyword(s) procesadas."
        user_state.progress = 100
        user_state.finished_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_state.add_log("SUCCESS", f"Pipeline completado exitosamente. {len(result)} resultados.")

        # Commit estado de sesion a DB
        try:
            if user_state._db:
                db_gen = get_db()
                db = next(db_gen)
                db.merge(user_state._db)
                db.commit()
                db_gen.close()
        except Exception as se:
            logger.error("Error guardando estado de sesion: %s", se)

        # Guardar historial de busqueda
        if user_state.user_id:
            try:
                db_gen = get_db()
                db = next(db_gen)
                for res in result:
                    if res.get("category") != "Error":
                        history_entry = SearchHistory(
                            user_id=user_state.user_id,
                            keyword=res["keyword"],
                            country=country_code,
                            profile=profile,
                            json_data=json.dumps(res, ensure_ascii=False)
                        )
                        db.add(history_entry)
                db.commit()
                db_gen.close()
                user_state.add_log("INFO", "Resultados guardados en tu Historial.")
            except Exception as dbe:
                logger.error("Error guardando historial en BD: %s", dbe)
                user_state.add_log("WARNING", "Error guardando en historial de BD.")

    except Exception as exc:
        logger.exception("Error en pipeline")
        user_state.error_msg = "Error en el pipeline."
        user_state.status_msg = "Error: hubo un problema procesando las keywords."
        user_state.add_log("ERROR", "Pipeline fallo. Revisa los logs del servidor.")
    finally:
        user_state.is_running = False
        # Commit final del estado
        try:
            if user_state._db:
                db = SessionLocal()
                db.merge(user_state._db)
                db.commit()
                db.close()
        except Exception:
            pass


def _blocking_pipeline(user_state: SessionState, keywords: List[str], country_code: str, profile: str) -> List[dict]:
    """Motor de scraping sincrónico (se corre en thread pool)."""
    from config import normalize_country
    from scraper.autocomplete import get_autocomplete_suggestions, get_question_suggestions
    from scraper.google_serp import scrape_google
    from scraper.volume_estimator import estimar_volumenes
    from scraper.categorizer import auto_categorizar

    ctx = normalize_country(country_code)
    ctx["scrape_profile"] = profile
    all_results = []
    total = len(keywords)

    for idx, kw in enumerate(keywords, start=1):
        try:
            base_prog = int(((idx - 1) / total) * 90)
            step_size = int(90 / total)
            
            user_state.add_log("INFO", f"[{idx}/{total}] Procesando: {kw}")

            user_state.status_msg = f"[{idx}/{total}] 🔍 Multi-Motor (Google/YT/Amazon/Bing): {kw}"
            user_state.progress = max(1, base_prog + int(step_size * 0.15))
            es_extremo = (profile.lower() == "extreme")
            sug = get_autocomplete_suggestions(kw, expandir=es_extremo, search_context=ctx)
            user_state.add_log("INFO", f"  → {len(sug)} sugerencias multi-motor obtenidas")

            user_state.status_msg = f"[{idx}/{total}] ❓ Preguntas & PAA: {kw}"
            user_state.progress = base_prog + int(step_size * 0.35)
            preg_ac = get_question_suggestions(kw, search_context=ctx)
            serp = scrape_google(kw, search_context=ctx)
            paa = serp.get("preguntas_paa", [])
            rel = serp.get("busquedas_relacionadas", [])
            user_state.add_log("INFO", f"  → {len(preg_ac)} preguntas autocompletado, {len(paa)} PAA, {len(rel)} relacionadas")

            from config import GROQ_API_KEY
            ai_clusters = []
            ai_intents = {}
            if GROQ_API_KEY:
                from scraper.ai_filter import filtrar_con_ia
                from scraper.ai_generator import clasificar_intencion_ia, generar_clusters_tematicos
                country_name = ctx.get("country_name", "Colombia")
                sug = filtrar_con_ia(sug, kw, country_name) if sug else sug
                preg_ac = filtrar_con_ia(preg_ac, kw, country_name) if preg_ac else preg_ac
                paa = filtrar_con_ia(paa, kw, country_name) if paa else paa
                rel = filtrar_con_ia(rel, kw, country_name) if rel else rel

                user_state.status_msg = f"[{idx}/{total}] 🤖 IA Groq (Clustering & Intención): {kw}"
                top_for_ai = (sug[:15] + paa[:10] + rel[:10])
                ai_intents = clasificar_intencion_ia(top_for_ai, kw, country_name)
                ai_clusters = generar_clusters_tematicos(top_for_ai, kw)
                user_state.add_log("INFO", f"  → {len(ai_clusters)} clusters semánticos generados con IA")

            user_state.status_msg = f"[{idx}/{total}] 📊 Métricas Cuantitativas & Trends: {kw}"
            user_state.progress = base_prog + int(step_size * 0.75)
            cat, sub = auto_categorizar(kw)
            vol = estimar_volumenes(
                keyword_principal=kw,
                sugerencias=sug,
                preguntas_paa=paa,
                preguntas_autocompletado=preg_ac,
                busquedas_relacionadas=rel,
                usar_trends=True,
                search_context=ctx,
                metadata={"categoria_padre": cat, "subcategoria": sub, "referencia": kw},
            )

            # Integrar intenciones detalladas de IA a las métricas si están disponibles
            if ai_intents:
                for k_text, ai_meta in ai_intents.items():
                    if k_text in vol and isinstance(ai_meta, dict):
                        if "intencion" in ai_meta:
                            vol[k_text]["intencion"] = ai_meta["intencion"]
                        if "funnel" in ai_meta:
                            vol[k_text]["funnel"] = ai_meta["funnel"]
                        if "formato_recomendado" in ai_meta:
                            vol[k_text]["formato_recomendado"] = ai_meta["formato_recomendado"]

            # Google Ads opcional (fallback silencioso)
            google_ads_res = {"enabled": False, "reason": "No configurado (usando suite gratuita)"}
            try:
                from scraper.google_ads_metrics import enrich_with_google_ads_metrics
                google_ads_res = enrich_with_google_ads_metrics(vol)
                if google_ads_res.get("enabled"):
                    user_state.add_log("INFO", "  → Google Ads OK")
            except Exception:
                pass

            # Generar Meta Tags, Schema FAQPage, Copies de Ads, KGR y Estudio Editorial
            from scraper.ai_generator import generar_schema_y_meta_tags, generar_copywriting_ads_y_hooks
            from scraper.kgr_estimator import estimar_kgr
            from scraper.editorial_ideator import obtener_tags_reales_google, generar_ideas_notas_angulos, redactar_nota_editorial

            c_name = ctx.get("country_name", "Colombia")
            all_questions = (paa + preg_ac)
            seo_schema = generar_schema_y_meta_tags(kw, all_questions, pais=c_name)
            ads_copy = generar_copywriting_ads_y_hooks(kw, all_questions, intencion=cat, pais=c_name)

            # Generación automática del módulo editorial en el Pipeline
            user_state.status_msg = f"[{idx}/{total}] ✍️ Estudio Editorial & Tags Google Trends: {kw}"
            editorial_tags = obtener_tags_reales_google(kw, sugerencias=sug, preguntas_paa=paa, pais=c_name)
            editorial_ideas = generar_ideas_notas_angulos(kw, sugerencias=sug, preguntas_paa=paa, pais=c_name, tags_reales=editorial_tags)
            editorial_nota = redactar_nota_editorial(
                kw,
                angulo=editorial_ideas[0]["angulo"] if editorial_ideas else "Trucos y Hacks Cotidianos",
                titular_h1=editorial_ideas[0].get("titular_h1") if editorial_ideas else None,
                sugerencias=sug,
                preguntas_paa=paa,
                pais=c_name,
                tags_reales=editorial_tags
            )
            user_state.add_log("INFO", f"  → 5 ideas de notas, tags reales y artículo editorial listos")

            serp_analysis = serp.get("serp_analysis", {})
            exact_count = serp_analysis.get("exact_match_count", 1) if serp_analysis else 1
            main_kw_score = vol.get(kw, {}).get("score", 50.0) if vol else 50.0
            kgr_data = estimar_kgr(kw, score_demanda=main_kw_score, exact_match_serp_count=exact_count)

            if serp_analysis.get("es_oportunidad_oro"):
                user_state.add_log("SUCCESS", f"  ⭐ Oportunidad de Oro en '{kw}': {serp_analysis.get('dificultad_estimada')}")

            user_state.progress = base_prog + step_size
            all_results.append({
                "keyword": kw,
                "country_name": c_name,
                "country_code": ctx.get("country_code", "CO").upper(),
                "category": cat,
                "subcategory": sub,
                "metrics": vol,
                "suggestions_count": len(sug),
                "paa_count": len(paa),
                "related_count": len(rel),
                "suggestions": sug,
                "paa": paa,
                "related": rel,
                "preguntas_autocompletado": preg_ac,
                "seo_schema": seo_schema,
                "ads_copy": ads_copy,
                "kgr_data": kgr_data,
                "serp_analysis": serp_analysis,
                "google_ads": google_ads_res,
                "editorial_tags": editorial_tags,
                "editorial_ideas": editorial_ideas,
                "editorial_nota": editorial_nota,
            })






        except Exception as e:
            user_state.add_log("ERROR", f"  Error procesando '{kw}'.")
            all_results.append({
                "keyword": kw,
                "category": "Error",
                "subcategory": "Error",
                "metrics": {},
                "suggestions_count": 0,
                "paa_count": 0,
                "related_count": 0,
                "suggestions": [],
                "paa": [],
                "related": [],
                "preguntas_autocompletado": [],
                "error": str(e),
                "google_ads": {},
            })

    return all_results


# ── Punto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
