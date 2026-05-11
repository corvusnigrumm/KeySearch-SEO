"""
KeySearch V 6.0 - FastAPI Web Server
=====================================
Servidor web para la interfaz de usuario de KeySearch.
Compatible con despliegue en Render.com (gratuito).

Variables de entorno necesarias (configurar en Render):
  - GROQ_API_KEY (opcional, para enriquecimiento IA)
  - GOOGLE_ADS_CUSTOMER_ID (opcional)
"""

import os
import sys
import asyncio
import logging
from typing import List, Optional

# Cargar .env local si existe (solo para desarrollo local, NO en producción)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # En Render.com no hace falta, las vars vienen del dashboard


from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("keysearch")

# ── Rutas absolutas para encontrar templates desde cualquier entorno ──────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="KeySearch V 6.0", version="6.0")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ── Estado global de sesión ───────────────────────────────────────────────────
class SessionState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.keywords: List[str] = []
        self.is_running: bool = False
        self.progress: int = 0
        self.status_msg: str = "Listo. Ingresa keywords para comenzar."
        self.last_run_data: Optional[List[dict]] = None
        self.error_msg: Optional[str] = None


state = SessionState()


# ── Rutas HTML ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"state": state}
    )


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="input.html",
        context={"state": state}
    )


# ── API: Estado del pipeline ──────────────────────────────────────────────────
@app.get("/status")
async def get_status():
    return {
        "is_running": state.is_running,
        "progress": state.progress,
        "status_msg": state.status_msg,
        "keywords_count": len(state.keywords),
        "error": state.error_msg,
    }


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
    state.is_running = True
    state.progress = 0
    state.status_msg = f"Iniciando pipeline para {len(kw_list)} keyword(s)..."
    state.error_msg = None

    background_tasks.add_task(_run_pipeline_task, kw_list, country, profile)

    return JSONResponse({"status": "success", "message": "Pipeline iniciado."})


# ── Tarea asíncrona del pipeline ──────────────────────────────────────────────
async def _run_pipeline_task(keywords: List[str], country_code: str, profile: str):
    """Ejecuta el scraping en segundo plano sin bloquear el servidor."""
    try:
        # Importar módulos pesados SOLO en el momento de ejecución
        logger.info("Cargando módulos del motor de scraping...")

        # Usamos run_in_executor para no bloquear el event loop con imports sincrónicos
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _blocking_pipeline, keywords, country_code, profile
        )

        state.last_run_data = result
        state.status_msg = f"✅ Pipeline completado. {len(result)} keyword(s) procesadas."
        state.progress = 100

    except Exception as exc:
        logger.exception("Error en pipeline")
        state.error_msg = str(exc)
        state.status_msg = f"❌ Error: {exc}"
    finally:
        state.is_running = False


def _blocking_pipeline(keywords: List[str], country_code: str, profile: str) -> List[dict]:
    """Ejecuta el pipeline de scraping de forma sincrónica (se corre en un thread aparte)."""
    # Importar aquí dentro evita que bloqueen el startup del servidor
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
        base_pct = int(((idx - 1) / total) * 100)

        state.status_msg = f"[{idx}/{total}] 🔍 Autocompletado: {kw}"
        state.progress = base_pct + 5
        sug = get_autocomplete_suggestions(kw, expandir=True, search_context=ctx)

        state.status_msg = f"[{idx}/{total}] ❓ Preguntas: {kw}"
        state.progress = base_pct + 10
        preg_ac = get_question_suggestions(kw, search_context=ctx)

        state.status_msg = f"[{idx}/{total}] 🌐 SERP Google: {kw}"
        state.progress = base_pct + 15
        serp = scrape_google(kw, search_context=ctx)
        paa = serp.get("preguntas_paa", [])
        rel = serp.get("busquedas_relacionadas", [])

        state.status_msg = f"[{idx}/{total}] 📊 Estimando volumen: {kw}"
        state.progress = base_pct + 18
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

        # Enriquecimiento con Google Ads (silencioso si no está configurado)
        try:
            from scraper.google_ads_metrics import enrich_with_google_ads_metrics
            state.status_msg = f"[{idx}/{total}] 💰 Google Ads: {kw}"
            enrich_with_google_ads_metrics(vol)
        except Exception:
            pass  # Google Ads es opcional

        state.progress = int((idx / total) * 100)
        all_results.append({
            "keyword": kw,
            "category": cat,
            "subcategory": sub,
            "metrics": vol,
            "suggestions_count": len(sug),
            "paa_count": len(paa),
        })

    return all_results


# ── Punto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
