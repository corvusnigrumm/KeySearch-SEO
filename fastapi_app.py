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
from typing import List, Optional, Dict, Any

# Cargar .env local si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("keysearch")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="KeySearch V 6.0", version="6.0")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ── Estado global de sesión ───────────────────────────────────────────────────
class SessionState:
    def __init__(self):
        self.reset()
        self.logs: List[Dict[str, str]] = []

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


state = SessionState()


# ── Helpers de contexto ───────────────────────────────────────────────────────
def _base_ctx(request: Request) -> dict:
    """Contexto base para todos los templates."""
    return {
        "state": state,
        "groq_active": bool(os.getenv("GROQ_API_KEY", "")),
        "google_ads_active": bool(os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")),
    }


# ── Rutas HTML ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context=_base_ctx(request))


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse(request=request, name="input.html", context=_base_ctx(request))


@app.get("/scraping", response_class=HTMLResponse)
async def scraping_page(request: Request):
    return templates.TemplateResponse(request=request, name="scraping.html", context=_base_ctx(request))


@app.get("/ia", response_class=HTMLResponse)
async def ia_page(request: Request):
    return templates.TemplateResponse(request=request, name="ia.html", context=_base_ctx(request))


@app.get("/export", response_class=HTMLResponse)
async def export_page(request: Request):
    return templates.TemplateResponse(request=request, name="export.html", context=_base_ctx(request))


@app.get("/api-status", response_class=HTMLResponse)
async def api_status_page(request: Request):
    return templates.TemplateResponse(request=request, name="api_status.html", context=_base_ctx(request))


@app.get("/logs-view", response_class=HTMLResponse)
async def logs_page(request: Request):
    return templates.TemplateResponse(request=request, name="logs.html", context=_base_ctx(request))


# ── API: Estado del pipeline ──────────────────────────────────────────────────
@app.get("/status")
async def get_status():
    return {
        "is_running": state.is_running,
        "progress": state.progress,
        "status_msg": state.status_msg,
        "keywords_count": len(state.keywords),
        "results_count": len(state.last_run_data) if state.last_run_data else 0,
        "error": state.error_msg,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
    }


@app.get("/api/logs")
async def get_logs():
    return {"logs": state.logs}


# ── API: Iniciar pipeline ─────────────────────────────────────────────────────
@app.post("/run")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    keywords: str = Form(...),
    country: str = Form("co"),
    profile: str = Form("normal"),
):
    if state.is_running:
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

    state.reset()
    state.keywords = kw_list
    state.country = country
    state.profile = profile
    state.is_running = True
    state.progress = 0
    state.status_msg = f"Iniciando pipeline para {len(kw_list)} keyword(s)..."
    state.started_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state.add_log("INFO", f"Pipeline iniciado: {len(kw_list)} keywords | País: {country} | Perfil: {profile}")

    background_tasks.add_task(_run_pipeline_task, kw_list, country, profile)
    return JSONResponse({"status": "success", "message": "Pipeline iniciado."})


# ── Descarga de resultados ────────────────────────────────────────────────────
from fastapi.responses import FileResponse

@app.get("/download/excel")
async def download_excel():
    if not state.last_run_data:
        return JSONResponse({"error": "No hay datos para exportar. Ejecuta primero el pipeline."}, status_code=404)

    from exporters.excel_export import exportar_excel

    volumenes = {}
    sugerencias = []
    preguntas_paa = []
    preguntas_ac = []
    relacionadas = []
    
    for item in state.last_run_data:
        volumenes.update(item.get("metrics", {}))
        sugerencias.extend(item.get("suggestions", []))
        preguntas_paa.extend(item.get("paa", []))
        preguntas_ac.extend(item.get("preguntas_autocompletado", []))
        relacionadas.extend(item.get("related", []))
        
    sugerencias = list(dict.fromkeys(sugerencias))
    preguntas_paa = list(dict.fromkeys(preguntas_paa))
    preguntas_ac = list(dict.fromkeys(preguntas_ac))
    relacionadas = list(dict.fromkeys(relacionadas))

    datos = {
        "volumenes": volumenes,
        "language_code": state.country.split("-")[0] if "-" in state.country else state.country,
        "sugerencias": sugerencias,
        "preguntas_paa": preguntas_paa,
        "preguntas_autocompletado": preguntas_ac,
        "busquedas_relacionadas": relacionadas,
    }

    keyword_principal = state.last_run_data[0]["keyword"] if len(state.last_run_data) == 1 else "Batch_Lote"
    
    try:
        ruta_archivo = exportar_excel(keyword_principal, datos)
        filename = os.path.basename(ruta_archivo)
        return FileResponse(
            ruta_archivo, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )
    except Exception as e:
        logger.exception("Error generando Excel")
        return JSONResponse({"error": f"Error generando Excel: {e}"}, status_code=500)



@app.get("/download/json")
async def download_json():
    if not state.last_run_data:
        return JSONResponse({"error": "No hay datos para exportar."}, status_code=404)

    data = {
        "meta": {
            "generated_at": state.finished_at or datetime.datetime.now().isoformat(),
            "country": state.country,
            "profile": state.profile,
            "total_keywords": len(state.last_run_data),
        },
        "results": state.last_run_data,
    }

    filename = f"keysearch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        iter([json.dumps(data, ensure_ascii=False, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Tarea asíncrona del pipeline ──────────────────────────────────────────────
async def _run_pipeline_task(keywords: List[str], country_code: str, profile: str):
    try:
        state.add_log("INFO", "Cargando módulos del motor de scraping...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _blocking_pipeline, keywords, country_code, profile
        )
        state.last_run_data = result
        state.status_msg = f"✅ Completado. {len(result)} keyword(s) procesadas."
        state.progress = 100
        state.finished_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state.add_log("SUCCESS", f"Pipeline completado exitosamente. {len(result)} resultados.")
    except Exception as exc:
        logger.exception("Error en pipeline")
        state.error_msg = str(exc)
        state.status_msg = f"❌ Error: {exc}"
        state.add_log("ERROR", f"Pipeline falló: {exc}")
    finally:
        state.is_running = False


def _blocking_pipeline(keywords: List[str], country_code: str, profile: str) -> List[dict]:
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
            state.add_log("INFO", f"[{idx}/{total}] Procesando: {kw}")

            state.status_msg = f"[{idx}/{total}] 🔍 Autocompletado: {kw}"
            state.progress = max(1, int(((idx - 1) / total) * 85))
            sug = get_autocomplete_suggestions(kw, expandir=True, search_context=ctx)
            state.add_log("INFO", f"  → {len(sug)} sugerencias de autocompletado")

            state.status_msg = f"[{idx}/{total}] ❓ Preguntas: {kw}"
            preg_ac = get_question_suggestions(kw, search_context=ctx)
            state.add_log("INFO", f"  → {len(preg_ac)} preguntas generadas")

            state.status_msg = f"[{idx}/{total}] 🌐 SERP Google: {kw}"
            serp = scrape_google(kw, search_context=ctx)
            paa = serp.get("preguntas_paa", [])
            rel = serp.get("busquedas_relacionadas", [])
            state.add_log("INFO", f"  → {len(paa)} PAA, {len(rel)} búsquedas relacionadas")

            state.status_msg = f"[{idx}/{total}] 📊 Volumen: {kw}"
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
                enrich_with_google_ads_metrics(vol)
                state.add_log("INFO", f"  → Google Ads OK")
            except Exception as e:
                state.add_log("WARNING", f"  → Google Ads no disponible: {e}")

            state.progress = int((idx / total) * 85)
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
            })

        except Exception as e:
            state.add_log("ERROR", f"  ✗ Error en '{kw}': {e}")
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
            })

    return all_results


# ── Punto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
