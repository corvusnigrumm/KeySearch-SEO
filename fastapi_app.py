"""
KeySearch V 6.0 - FastAPI Web Server (Versión Completa)
========================================================
Todas las rutas funcionales:
  GET  /             → Dashboard
  GET  /config       → Configuración de búsqueda  
  GET  /scraping     → Módulo de scraping (vista detallada)
  GET  /ia           → IA Enrichment
  GET  /export       → Exportación
  GET  /api-status   → Estado de APIs
  GET  /logs         → Logs del sistema
  POST /run          → Iniciar pipeline
  GET  /status       → Estado JSON del pipeline (polling)
  GET  /download/csv → Descargar resultados como CSV
  GET  /download/json → Descargar resultados como JSON
"""

import os
import io
import csv
import json
import asyncio
import logging
import datetime
import uuid
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
from core.auth import verify_password, get_password_hash, create_access_token, decode_access_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("keysearch")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="KeySearch V 6.0", version="6.0")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

import urllib.request

def ping_render():
    # Evita que la instancia gratuita de Render se apague (spin down)
    url = "https://keysearch-seo-1.onrender.com/api-status"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (KeepAlive)'})
        with urllib.request.urlopen(req) as response:
            logger.info(f"Keep-alive ping sent. Status: {response.status}")
    except Exception as e:
        logger.warning(f"Keep-alive ping failed: {e}")

async def keep_alive_task():
    while True:
        await asyncio.sleep(14 * 60)  # Ping cada 14 minutos
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, ping_render)

@app.on_event("startup")
async def on_startup():
    init_db()
    asyncio.create_task(keep_alive_task())

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

def _base_ctx(request: Request, user: User = None) -> dict:
    """Contexto base para todos los templates."""
    return {
        "state": get_session(request),
        "groq_active": bool(os.getenv("GROQ_API_KEY", "")),
        "google_ads_active": bool(os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")),
        "current_user": user,
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

            user_state.status_msg = f"[{idx}/{total}] 🔍 Autocompletado: {kw}"
            user_state.progress = max(1, base_prog + int(step_size * 0.1))
            es_extremo = (profile.lower() == "extreme")
            sug = get_autocomplete_suggestions(kw, expandir=es_extremo, search_context=ctx)
            user_state.add_log("INFO", f"  → {len(sug)} sugerencias de autocompletado")

            user_state.status_msg = f"[{idx}/{total}] ❓ Preguntas: {kw}"
            user_state.progress = base_prog + int(step_size * 0.4)
            preg_ac = get_question_suggestions(kw, search_context=ctx)
            user_state.add_log("INFO", f"  → {len(preg_ac)} preguntas generadas")

            user_state.status_msg = f"[{idx}/{total}] 🌐 SERP Google: {kw}"
            user_state.progress = base_prog + int(step_size * 0.6)
            serp = scrape_google(kw, search_context=ctx)
            paa = serp.get("preguntas_paa", [])
            rel = serp.get("busquedas_relacionadas", [])
            user_state.add_log("INFO", f"  → {len(paa)} PAA, {len(rel)} búsquedas relacionadas")

            from config import GROQ_API_KEY
            if GROQ_API_KEY:
                from scraper.ai_filter import filtrar_con_ia
                country_name = ctx.get("country_name", "Colombia")
                sug = filtrar_con_ia(sug, kw, country_name) if sug else sug
                preg_ac = filtrar_con_ia(preg_ac, kw, country_name) if preg_ac else preg_ac
                paa = filtrar_con_ia(paa, kw, country_name) if paa else paa
                rel = filtrar_con_ia(rel, kw, country_name) if rel else rel

            user_state.status_msg = f"[{idx}/{total}] 📊 Volumen: {kw}"
            user_state.progress = base_prog + int(step_size * 0.8)
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

            try:
                from scraper.google_ads_metrics import enrich_with_google_ads_metrics
                google_ads_res = enrich_with_google_ads_metrics(vol)
                user_state.add_log("INFO", f"  → Google Ads OK")
            except Exception as e:
                google_ads_res = {"enabled": False, "reason": str(e)}
                user_state.add_log("WARNING", f"  → Google Ads no disponible: {e}")

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
