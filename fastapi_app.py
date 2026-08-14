"""
Key Search V 10.0 Ultra - FastAPI Web Server
============================================
Suite Profesional de SEO, Keyword Research, Content Briefs, Schema FAQ y Ads Copywriting.
"""

import os
import io
import csv
import json
import asyncio
import logging
import datetime
import uuid
import secrets
import urllib.parse
from typing import List, Optional, Dict, Any

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
from core.database import init_db, get_db, User, SearchHistory

import config
from core.auth import verify_password, get_password_hash, create_access_token, decode_access_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("keysearch")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="Key Search V 10.0 Ultra", version="10.0")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
async def on_startup():
    init_db()

# ── Estado global de sesión ───────────────────────────────────────────────────
class SessionState:
    def __init__(self):
        self.reset()
        self.logs: List[Dict[str, str]] = []
        self.user_id: Optional[int] = None

    def reset(self):
        self.keywords: List[str] = []
        self.is_running: bool = False
        self.progress: int = 0
        self.status_msg: str = "Listo. Ingresa keywords para comenzar."
        self.last_run_data: Optional[List[dict]] = None
        self.error_msg: Optional[str] = None
        self.country: str = "co"
        self.profile: str = "normal"
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None

    def add_log(self, level: str, message: str):
        entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "msg": message,
        }
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]


sessions: Dict[str, SessionState] = {}


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    is_new = False
    if not session_id:
        session_id = str(uuid.uuid4())
        is_new = True
    
    request.state.session_id = session_id
    
    if session_id not in sessions:
        sessions[session_id] = SessionState()
        
    response = await call_next(request)
    
    if is_new:
        response.set_cookie(key="session_id", value=session_id, max_age=86400 * 30)
    return response


def get_session(request: Request) -> SessionState:
    return sessions.get(request.state.session_id)


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
    """Devuelve diagnostico detallado de Google Ads para la UI."""
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
        "developer_token": yaml_vals.get("developer_token", ""),
        "client_id": yaml_vals.get("client_id", ""),
        "client_secret": yaml_vals.get("client_secret", ""),
        "refresh_token": yaml_vals.get("refresh_token", ""),
        "login_customer_id": yaml_vals.get("login_customer_id", ""),
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
        }
    }


# ── Rutas Autenticación ───────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user:
        return templates.TemplateResponse(request=request, name="login.html", context={"request": request, "error": "El perfil ya existe."})
    
    new_user = User(username=username, password_hash=get_password_hash(password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": str(new_user.id)})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request=request, name="login.html", context={"request": request, "error": "Contraseña o usuario incorrecto."})
    
    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.post("/api/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
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
async def clusters_page(request: Request, user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse(request=request, name="clusters_map.html", context=_base_ctx(request, user))


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


# ── API: Estado del pipeline ──────────────────────────────────────────────────
@app.get("/status")
async def get_status(request: Request):
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
async def get_logs(request: Request):
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
async def api_generate_schema(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Genera Meta Tags de Alto CTR y Schema JSON-LD (FAQPage) bajo demanda."""
    try:
        data = await request.json()
        kw = data.get("keyword", "").strip()
        questions = data.get("questions", [])
        country = data.get("country", "Colombia")
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.ai_filter import generar_schema_y_meta_tags
        schema_data = generar_schema_y_meta_tags(kw, questions, pais=country)
        return JSONResponse(schema_data)
    except Exception as e:
        logger.error(f"Error generando schema: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/generate-ads-copy")
async def api_generate_ads_copy(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Genera Copies de Google Ads, Facebook Ads y Hooks para TikTok bajo demanda."""
    try:
        data = await request.json()
        kw = data.get("keyword", "").strip()
        questions = data.get("questions", [])
        intent = data.get("intent", "Informativa / Comercial")
        country = data.get("country", "Colombia")
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.ai_filter import generar_ads_copy
        ads_data = generar_ads_copy(kw, preguntas=questions, intencion=intent, pais=country)
        return JSONResponse(ads_data)
    except Exception as e:
        logger.error(f"Error generando ads copy: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/generate-brief")
async def api_generate_brief(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Genera Content Brief Editorial (H1/H2/H3) para redactores bajo demanda."""
    try:
        data = await request.json()
        kw = data.get("keyword", "").strip()
        questions = data.get("questions", [])
        intent = data.get("intent", "Informativa")
        country = data.get("country", "Colombia")
        if not kw:
            return JSONResponse({"error": "Keyword requerida"}, status_code=400)

        from scraper.content_brief import generar_content_brief
        brief_data = generar_content_brief(kw, preguntas_paa=questions, intencion=intent, pais=country)
        return JSONResponse(brief_data)
    except Exception as e:
        logger.error(f"Error generando content brief: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/set-groq-model")
async def api_set_groq_model(request: Request, user: User = Depends(get_current_user_or_redirect)):
    """Cambia el modelo de Groq activo dinámicamente."""
    try:
        data = await request.json()
        model_id = data.get("model", "").strip()
        if not model_id:
            return JSONResponse({"error": "Modelo requerido"}, status_code=400)

        import config
        config.GROQ_MODEL = model_id
        logger.info("Modelo de Groq actualizado dinámicamente a: %s", model_id)
        return JSONResponse({"status": "ok", "current_model": model_id})
    except Exception as e:
        logger.error("Error cambiando modelo Groq: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)

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
            "country_name": item.get("country_name", ""),
            "country_code": item.get("country_code", ""),
            "category_name": item.get("category", ""),
            "subcategory_name": item.get("subcategory", ""),
            "google_ads": item.get("google_ads", {}),
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
        return JSONResponse({"error": f"Error generando Excel histórico: {e}"}, status_code=500)


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
            "country_name": item.get("country_name", ""),
            "country_code": item.get("country_code", ""),
            "category_name": item.get("category", ""),
            "subcategory_name": item.get("subcategory", ""),
            "google_ads": item.get("google_ads", {}),
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
            return JSONResponse({"error": f"Error generando Excel: {e}"}, status_code=500)
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
            return JSONResponse({"error": f"Error generando ZIP: {e}"}, status_code=500)



@app.get("/download/json")
async def download_json(request: Request):
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
    """Guarda la configuración de Google Ads en los archivos locales."""
    yaml_path = getattr(config, "GOOGLE_ADS_CONFIG_PATH", os.path.join(BASE_DIR, "google-ads.yaml"))
    cid_path = getattr(config, "GOOGLE_ADS_CUSTOMER_ID_FILE", os.path.join(BASE_DIR, "google-ads.customer-id.txt"))

    yaml_content = (
        f'developer_token: "{developer_token}"\n'
        f'client_id: "{client_id}"\n'
        f'client_secret: "{client_secret}"\n'
        f'refresh_token: "{refresh_token}"\n'
        f'login_customer_id: "{login_customer_id.replace("-", "").strip()}"\n'
        f'use_proto_plus: true\n'
    )
    try:
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        clean_cid = customer_id.replace("-", "").strip()
        with open(cid_path, "w", encoding="utf-8") as f:
            f.write(clean_cid)
        logger.info("Google Ads config guardada por %s", user.username)
        return JSONResponse({"status": "ok", "message": "Configuración de Google Ads guardada correctamente."})
    except Exception as exc:
        logger.exception("Error guardando config de Google Ads")
        return JSONResponse({"status": "error", "message": f"Error guardando: {exc}"}, status_code=500)


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
        return JSONResponse({"success": False, "detail": f"Error inesperado: {exc}"}, status_code=500)


@app.get("/api/google-ads/auth")
async def google_ads_oauth_start(request: Request):
    """Inicia el flujo OAuth de Google para obtener un refresh token."""
    yaml_path = getattr(config, "GOOGLE_ADS_CONFIG_PATH", os.path.join(BASE_DIR, "google-ads.yaml"))
    vals = config.parse_yaml_simple(yaml_path)
    cid = vals.get("client_id", "")
    csecret = vals.get("client_secret", "")
    if not cid or not csecret:
        return JSONResponse({"error": "Primero guarda client_id y client_secret en la configuración."}, status_code=400)

    state = secrets.token_urlsafe(24)
    # Construir redirect_uri basado en el host de la petición
    host = request.headers.get("host", "localhost:8001")
    scheme = request.headers.get("x-forwarded-proto", "http")
    redirect_uri = f"{scheme}://{host}/api/google-ads/callback"

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
        return HTMLResponse(f"<h2>Error de Google: {error}</h2><p><a href='/api-status'>Volver</a></p>", status_code=400)
    if state not in _oauth_states:
        return HTMLResponse("<h2>Estado inválido o expirado.</h2><p><a href='/api-status'>Volver</a></p>", status_code=400)

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
        return HTMLResponse(f"<h2>Error obteniendo tokens: {exc}</h2><p><a href='/api-status'>Volver</a></p>", status_code=500)

    new_refresh = token_data.get("refresh_token", "")
    if not new_refresh:
        return HTMLResponse("<h2>No se recibió refresh_token. Reintenta el flujo.</h2><p><a href='/api-status'>Volver</a></p>", status_code=400)

    # Leer yaml actual y sobrescribir refresh_token
    yaml_path = getattr(config, "GOOGLE_ADS_CONFIG_PATH", os.path.join(BASE_DIR, "google-ads.yaml"))
    vals = config.parse_yaml_simple(yaml_path)
    vals["refresh_token"] = new_refresh
    yaml_content = (
        f'developer_token: "{vals.get("developer_token", "")}"\n'
        f'client_id: "{vals.get("client_id", "")}"\n'
        f'client_secret: "{vals.get("client_secret", "")}"\n'
        f'refresh_token: "{new_refresh}"\n'
        f'login_customer_id: "{vals.get("login_customer_id", "")}"\n'
        f'use_proto_plus: true\n'
    )
    try:
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
    except Exception as exc:
        logger.exception("Error guardando refresh_token")
        return HTMLResponse(f"<h2>Token obtenido pero error guardando: {exc}</h2>", status_code=500)

    logger.info("Refresh token de Google Ads obtenido y guardado exitosamente.")
    return RedirectResponse("/api-status?oauth=success")


# ── Tarea asíncrona del pipeline ──────────────────────────────────────────────
async def _run_pipeline_task(user_state: SessionState, keywords: List[str], country_code: str, profile: str):
    try:
        user_state.add_log("INFO", "Cargando módulos del motor de scraping...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _blocking_pipeline, user_state, keywords, country_code, profile
        )
        user_state.last_run_data = result
        user_state.status_msg = f"✅ Completado. {len(result)} keyword(s) procesadas."
        user_state.progress = 100
        user_state.finished_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_state.add_log("SUCCESS", f"Pipeline completado exitosamente. {len(result)} resultados.")
        
        # Guardar en Base de Datos el historial de busqueda
        if user_state.user_id:
            try:
                # Usar un generador manual de db session porque estamos en background sin request
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
                logger.error(f"Error guardando historial en BD: {dbe}")
                user_state.add_log("WARNING", "Error guardando en historial de BD.")
                
    except Exception as exc:
        logger.exception("Error en pipeline")
        user_state.error_msg = str(exc)
        user_state.status_msg = f"❌ Error: {exc}"
        user_state.add_log("ERROR", f"Pipeline falló: {exc}")
    finally:
        user_state.is_running = False


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
                from scraper.ai_filter import filtrar_con_ia, clasificar_intencion_ia, generar_clusters_tematicos
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

            # Generar Meta Tags, Schema FAQPage, Copies de Ads, Content Brief y KGR
            from scraper.ai_filter import generar_schema_y_meta_tags, generar_copywriting_ads_y_hooks
            from scraper.content_brief import generar_content_brief
            from scraper.kgr_estimator import estimar_kgr

            c_name = ctx.get("country_name", "Colombia")
            all_questions = (paa + preg_ac)
            seo_schema = generar_schema_y_meta_tags(kw, all_questions, pais=c_name)
            ads_copy = generar_copywriting_ads_y_hooks(kw, all_questions, intencion=cat, pais=c_name)
            content_brief = generar_content_brief(kw, sugerencias=sug, preguntas_paa=paa, preguntas_ac=preg_ac, pais=c_name, intencion=cat)

            serp_analysis = serp.get("serp_analysis", {})
            exact_count = serp_analysis.get("exact_match_count", 1) if serp_analysis else 1
            main_kw_score = vol.get(kw, {}).get("score", 50.0) if vol else 50.0
            kgr_data = estimar_kgr(kw, score_demanda=main_kw_score, exact_match_serp_count=exact_count)

            if serp_analysis.get("es_oportunidad_oro"):
                user_state.add_log("SUCCESS", f"  ⭐ Oportunidad de Oro en '{kw}': {serp_analysis.get('dificultad_estimada')}")

            user_state.progress = base_prog + step_size
            all_results.append({
                "keyword": kw,
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
                "ai_clusters": ai_clusters,
                "seo_schema": seo_schema,
                "ads_copy": ads_copy,
                "content_brief": content_brief,
                "kgr_data": kgr_data,
                "serp_analysis": serp_analysis,
                "google_ads": google_ads_res,
            })






        except Exception as e:
            user_state.add_log("ERROR", f"  ✗ Error en '{kw}': {e}")
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
