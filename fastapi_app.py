import os
import json
import asyncio
import threading
from typing import List, Optional
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Importar lógica del motor
from config import normalize_country
from scraper.autocomplete import get_autocomplete_suggestions, get_question_suggestions
from scraper.google_serp import scrape_google
from scraper.volume_estimator import estimar_volumenes
from scraper.google_ads_metrics import enrich_with_google_ads_metrics
from scraper.categorizer import auto_categorizar

app = FastAPI(title="KeySearch V 6.0 - FastAPI Engine")

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Estado global simple (para demo)
# En una app real usaríamos Redis o una DB
class AppState:
    def __init__(self):
        self.keywords = []
        self.results = {}
        self.is_running = False
        self.progress = 0
        self.status_msg = "Esperando inicio..."
        self.last_run_data = None

state = AppState()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": state})

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse("input.html", {"request": request, "state": state})

@app.post("/run")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    keywords: str = Form(...),
    country: str = Form("co"),
    profile: str = Form("normal")
):
    if state.is_running:
        return JSONResponse({"status": "error", "message": "Pipeline already running"}, status_code=400)
    
    # Limpiar y parsear keywords
    kw_list = [k.strip() for k in keywords.replace(",", "\n").split("\n") if k.strip()]
    if not kw_list:
        return JSONResponse({"status": "error", "message": "No keywords provided"}, status_code=400)
    
    state.keywords = kw_list
    state.is_running = True
    state.progress = 0
    state.status_msg = f"Iniciando proceso para {len(kw_list)} keywords..."
    
    # Ejecutar en segundo plano
    background_tasks.add_task(execute_pipeline, kw_list, country, profile)
    
    return JSONResponse({"status": "success", "message": "Pipeline started"})

@app.get("/status")
async def get_status():
    return {
        "is_running": state.is_running,
        "progress": state.progress,
        "status_msg": state.status_msg,
        "keywords_count": len(state.keywords)
    }

async def execute_pipeline(keywords: List[str], country_code: str, profile: str):
    try:
        ctx = normalize_country(country_code)
        ctx["scrape_profile"] = profile
        
        all_results = []
        total_steps = len(keywords) * 5
        current_step = 0
        
        for kw in keywords:
            state.status_msg = f"Procesando: {kw}..."
            cat, sub = auto_categorizar(kw)
            
            # Autocomplete
            state.status_msg = f"[{kw}] Extrayendo autocompletado..."
            sug = get_autocomplete_suggestions(kw, expandir=True, search_context=ctx)
            current_step += 1
            state.progress = int((current_step / total_steps) * 100)
            
            # Preguntas
            state.status_msg = f"[{kw}] Generando preguntas..."
            preg_ac = get_question_suggestions(kw, search_context=ctx)
            current_step += 1
            state.progress = int((current_step / total_steps) * 100)
            
            # SERP
            state.status_msg = f"[{kw}] Extrayendo datos SERP..."
            serp = scrape_google(kw, search_context=ctx)
            paa = serp.get("preguntas_paa", [])
            rel = serp.get("busquedas_relacionadas", [])
            current_step += 1
            state.progress = int((current_step / total_steps) * 100)
            
            # Volúmenes
            state.status_msg = f"[{kw}] Analizando métricas..."
            vol = estimar_volumenes(
                keyword_principal=kw, sugerencias=sug, preguntas_paa=paa,
                preguntas_autocompletado=preg_ac, busquedas_relacionadas=rel,
                usar_trends=True, search_context=ctx,
                metadata={"categoria_padre": cat, "subcategoria": sub, "referencia": kw}
            )
            current_step += 1
            state.progress = int((current_step / total_steps) * 100)
            
            # Ads
            state.status_msg = f"[{kw}] Enriqueciendo con Ads..."
            enrich_with_google_ads_metrics(vol)
            current_step += 1
            state.progress = int((current_step / total_steps) * 100)
            
            all_results.append({
                "keyword": kw,
                "category": cat,
                "subcategory": sub,
                "metrics": vol
            })

        state.last_run_data = all_results
        state.status_msg = "Pipeline completado con éxito."
        state.progress = 100
    except Exception as e:
        state.status_msg = f"Error en pipeline: {str(e)}"
    finally:
        state.is_running = False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
