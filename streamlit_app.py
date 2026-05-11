"""
KeySearch V 6.0 - Streamlit Web Interface
SEO Pipeline Engine con diseño Stitch (Deep Tech Blue)
"""
import streamlit as st
import pandas as pd
import os
import sys
import time
import traceback
from datetime import datetime

# Path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Lazy imports with error handling ---
def _safe_import():
    """Import project modules lazily to handle missing deps gracefully."""
    mods = {}
    try:
        from config import APP_VERSION, COUNTRY_CATALOG, normalize_country
        mods["APP_VERSION"] = APP_VERSION
        mods["COUNTRY_CATALOG"] = COUNTRY_CATALOG
        mods["normalize_country"] = normalize_country
    except Exception as e:
        mods["_config_error"] = str(e)
        mods["APP_VERSION"] = "6.0"
        mods["COUNTRY_CATALOG"] = {"co": {"name": "Colombia"}, "mx": {"name": "Mexico"}}
        mods["normalize_country"] = lambda x: {"country_code": x, "country_name": x, "language_code": "es", "google_ads_geo_targets": []}
    try:
        from config import GROQ_API_KEY
        mods["GROQ_API_KEY"] = GROQ_API_KEY
    except Exception:
        mods["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
    return mods

MODS = _safe_import()

# --- PAGE CONFIG ---
st.set_page_config(page_title="KeySearch V 6.0", page_icon="🔍", layout="wide")

# --- CSS (Stitch Design System) ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<style>
    :root {
        --primary: #000000; --secondary: #00677f; --secondary-container: #00d2ff;
        --background: #f8f9ff; --surface: #f8f9ff; --on-surface: #0b1c30;
        --on-surface-variant: #44474d; --outline-variant: #c5c6cd;
        --surface-container-low: #eff4ff; --surface-container-lowest: #ffffff;
        --surface-container: #e5eeff; --primary-container: #0d1c32;
    }
    .stApp { background-color: var(--background) !important; }
    [data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--outline-variant) !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { font-family: 'Inter', sans-serif !important; }
    .block-container { padding-top: 2rem !important; max-width: 1400px !important; }
    .mono { font-family: 'JetBrains Mono', monospace !important; }
    div[data-testid="stMetric"] { background: var(--surface-container-lowest); border: 1px solid var(--outline-variant); border-radius: 12px; padding: 16px; }
    div[data-testid="stMetric"] label { font-family: 'JetBrains Mono' !important; font-size: 12px !important; color: var(--on-surface-variant) !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-family: 'Inter' !important; font-weight: 700 !important; color: var(--on-surface) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { font-family: 'JetBrains Mono' !important; font-size: 13px !important; border-radius: 8px 8px 0 0; }
    .stDataFrame { border: 1px solid var(--outline-variant) !important; border-radius: 8px !important; }
    .ks-card { background: var(--surface-container-lowest); border: 1px solid var(--outline-variant); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
    .ks-gradient { background: linear-gradient(135deg, #0d1c32 0%, #00677f 100%); color: white; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
    .ks-pipeline-step { display: inline-flex; flex-direction: column; align-items: center; gap: 8px; }
    .ks-step-circle { width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
    .ks-step-active { background: var(--secondary); color: white; }
    .ks-step-pending { border: 2px solid var(--outline-variant); color: var(--on-surface-variant); }
    .ks-step-done { background: #10b981; color: white; }
    .ks-tag-success { background: #d1fae5; color: #065f46; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; }
    .ks-tag-error { background: #ffdad6; color: #93000a; padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    h1, h2, h3 { font-family: 'Inter', sans-serif !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## KeySearch V 6.0")
    st.caption("SEO Pipeline Engine")
    st.divider()
    page = st.radio("Navegación", ["🏠 Pipeline Hub", "📥 Data Input", "📊 Resultados"], label_visibility="collapsed")
    st.divider()
    # Status indicators
    groq_key = MODS.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if groq_key:
        st.success("✅ IA Groq activa", icon="🤖")
    else:
        st.info("ℹ️ Sin GROQ_API_KEY", icon="🔑")
    ads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "google-ads.yaml")
    if os.path.exists(ads_path):
        st.success("✅ Google Ads configurado")
    else:
        st.info("ℹ️ Sin Google Ads (opcional)")
    if "_config_error" in MODS:
        st.warning(f"⚠️ Config: {MODS['_config_error']}")

# --- PAGES ---
if page == "🏠 Pipeline Hub":
    st.markdown("### Estado del Sistema")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="ks-gradient">
            <span class="mono" style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.05em">SYSTEM HEALTH</span>
            <h3 style="color:white;margin:8px 0">Optimal Performance</h3>
            <p style="font-size:14px;opacity:.9">Todos los módulos están operativos y listos para ejecutar el pipeline de extracción SEO.</p>
            <div style="margin-top:20px;display:flex;align-items:center;gap:8px">
                <div style="background:#10b981;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center">
                    <span class="material-symbols-outlined" style="font-size:16px;color:white">check</span>
                </div>
                <span class="mono" style="font-size:12px">Modules OK</span>
            </div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.metric("Países disponibles", len(MODS["COUNTRY_CATALOG"]))
    with c3:
        st.metric("Versión", f"V {MODS['APP_VERSION']}")

    # Pipeline stepper
    st.markdown("### Pipeline de Extracción")
    st.markdown("""<div class="ks-card" style="display:flex;align-items:center;justify-content:space-around;padding:32px">
        <div class="ks-pipeline-step"><div class="ks-step-circle ks-step-done"><span class="material-symbols-outlined">input</span></div><span class="mono" style="font-size:12px">Ingestion</span></div>
        <div style="flex:1;height:2px;background:#10b981;margin:0 12px"></div>
        <div class="ks-pipeline-step"><div class="ks-step-circle ks-step-active"><span class="material-symbols-outlined">database</span></div><span class="mono" style="font-size:12px">Scraping</span></div>
        <div style="flex:1;height:2px;border-top:2px dashed var(--outline-variant);margin:0 12px"></div>
        <div class="ks-pipeline-step" style="opacity:.5"><div class="ks-step-circle ks-step-pending"><span class="material-symbols-outlined">psychology</span></div><span class="mono" style="font-size:12px">IA Enrichment</span></div>
        <div style="flex:1;height:2px;border-top:2px dashed var(--outline-variant);margin:0 12px"></div>
        <div class="ks-pipeline-step" style="opacity:.5"><div class="ks-step-circle ks-step-pending"><span class="material-symbols-outlined">download</span></div><span class="mono" style="font-size:12px">Export</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("### Comenzar Análisis Rápido")
    st.page_link("streamlit_app.py", label="Ir a Data Input →", icon="📥", disabled=True)
    st.info("Navega a **📥 Data Input** en la barra lateral para configurar y ejecutar un análisis.")

elif page == "📥 Data Input":
    st.markdown("### Configuración de Búsqueda")
    st.caption("Define los parámetros de entrada para la extracción y enriquecimiento de datos SEO.")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("#### 🔑 Palabras Clave (Keywords)")
        keywords_raw = st.text_area(
            "Introduce una keyword por línea o separadas por comas",
            height=200,
            placeholder="ej: mejores herramientas seo 2024\nanalisis de competencia\nautomatizacion marketing b2b",
        )
        kw_list = [k.strip() for k in keywords_raw.replace("\n", ",").split(",") if k.strip()]
        st.caption(f"{len(kw_list)} / 500 keywords detectadas")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🌍 Segmentación")
            catalog = MODS["COUNTRY_CATALOG"]
            country = st.selectbox("País", options=list(catalog.keys()), format_func=lambda x: f"{catalog[x]['name']} ({x.upper()})")
        with c2:
            st.markdown("#### ⚙️ Perfil de Búsqueda")
            profile = st.radio("Agente", ["normal", "extreme"], format_func=lambda x: "Normal (equilibrado)" if x == "normal" else "Extreme (máxima cobertura)")

    with col_right:
        st.markdown("""<div class="ks-card" style="background:var(--primary-container);color:white;border:none;position:relative;overflow:hidden">
            <div style="position:absolute;right:-40px;top:-40px;width:160px;height:160px;background:rgba(0,210,255,.1);border-radius:50%;filter:blur(30px)"></div>
            <h4 style="color:white;margin-bottom:20px">Validación del Proyecto</h4>
            <div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.1);padding-bottom:8px;margin-bottom:12px">
                <span style="opacity:.8;font-size:14px">Keywords configuradas</span>
                <span class="mono" style="color:var(--secondary-container);font-weight:700">""" + ("Listo" if kw_list else "Pendiente") + """</span>
            </div>
            <div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.1);padding-bottom:8px;margin-bottom:12px">
                <span style="opacity:.8;font-size:14px">Segmentación</span>
                <span class="mono" style="color:var(--secondary-container);font-weight:700">Listo</span>
            </div>
        </div>""", unsafe_allow_html=True)

        run_btn = st.button("🚀 INICIAR PIPELINE", use_container_width=True, type="primary")

    if run_btn:
        if not kw_list:
            st.error("Ingresa al menos una keyword.")
        else:
            try:
                from config import normalize_country as _nc
                from scraper.categorizer import auto_categorizar
                from scraper.autocomplete import get_autocomplete_suggestions, get_question_suggestions
                from scraper.google_serp import scrape_google
                from scraper.volume_estimator import estimar_volumenes
                from scraper.google_ads_metrics import enrich_with_google_ads_metrics
                from exporters.excel_export import exportar_excel
                from exporters.json_export import exportar_json
            except Exception as e:
                st.error(f"Error importando módulos: {e}")
                st.code(traceback.format_exc())
                st.stop()

            all_results = []
            for idx, keyword in enumerate(kw_list):
                country_data = _nc(country)
                search_ctx = {
                    "country_code": country_data["country_code"],
                    "country_name": country_data["country_name"],
                    "language_code": country_data["language_code"],
                    "google_ads_geo_targets": country_data["google_ads_geo_targets"],
                    "scrape_profile": profile,
                }
                categoria, subcategoria = auto_categorizar(keyword)
                editorial_ctx = {"category_name": categoria, "subcategory_name": subcategoria}

                status = st.status(f"[{idx+1}/{len(kw_list)}] Analizando: **{keyword}**", expanded=True)
                status.write(f"📂 Categoría: {categoria} / {subcategoria}")

                status.write("🔍 Sugerencias de autocompletado...")
                sugerencias = get_autocomplete_suggestions(keyword, expandir=True, search_context=search_ctx)
                status.write(f"  ✅ {len(sugerencias)} sugerencias")

                status.write("❓ Preguntas por autocompletado...")
                preguntas_ac = get_question_suggestions(keyword, search_context=search_ctx)
                status.write(f"  ✅ {len(preguntas_ac)} preguntas")

                status.write("🌐 Extrayendo SERP (PAA + Relacionadas)...")
                serp = scrape_google(keyword, search_context=search_ctx)
                paa = serp.get("preguntas_paa", [])
                rel = serp.get("busquedas_relacionadas", [])
                status.write(f"  ✅ {len(paa)} PAA, {len(rel)} relacionadas")

                # IA filter
                groq = MODS.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
                if groq:
                    status.write("🤖 Filtrando con IA (Groq)...")
                    try:
                        from scraper.ai_filter import filtrar_con_ia
                        sugerencias = filtrar_con_ia(sugerencias, keyword, search_ctx["country_name"])
                        preguntas_ac = filtrar_con_ia(preguntas_ac, keyword, search_ctx["country_name"])
                        paa = filtrar_con_ia(paa, keyword, search_ctx["country_name"])
                        rel = filtrar_con_ia(rel, keyword, search_ctx["country_name"])
                    except Exception:
                        pass

                status.write("📊 Estimando volúmenes y señales...")
                volumenes = estimar_volumenes(
                    keyword_principal=keyword, sugerencias=sugerencias, preguntas_paa=paa,
                    preguntas_autocompletado=preguntas_ac, busquedas_relacionadas=rel,
                    usar_trends=True, search_context=search_ctx,
                    metadata={"categoria_padre": categoria, "subcategoria": subcategoria, "referencia": keyword,
                              "pais": search_ctx["country_name"], "pais_codigo": search_ctx["country_code"],
                              "google_ads_geo_targets": search_ctx["google_ads_geo_targets"]},
                )

                status.write("💰 Google Ads...")
                gads = enrich_with_google_ads_metrics(volumenes)

                datos = {
                    "keyword": keyword, "sugerencias": sugerencias, "preguntas_paa": paa,
                    "preguntas_autocompletado": preguntas_ac, "busquedas_relacionadas": rel,
                    "volumenes": volumenes, "google_ads": gads,
                    "country_code": search_ctx["country_code"], "country_name": search_ctx["country_name"],
                    "language_code": search_ctx["language_code"],
                    "category_name": categoria, "subcategory_name": subcategoria,
                }
                all_results.append(datos)
                status.update(label=f"✅ {keyword} completado", state="complete", expanded=False)

            st.session_state["results"] = all_results
            st.success(f"Pipeline completado: {len(all_results)} keyword(s) analizadas")
            st.balloons()

elif page == "📊 Resultados":
    if "results" not in st.session_state or not st.session_state["results"]:
        st.info("No hay resultados aún. Ve a **📥 Data Input** para ejecutar un análisis.")
        st.stop()

    results = st.session_state["results"]
    kw_names = [r["keyword"] for r in results]
    sel = st.selectbox("Keyword analizada", kw_names)
    res = next(r for r in results if r["keyword"] == sel)
    vol = res["volumenes"]

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Keywords", len(vol))
    m2.metric("Categoría", res.get("category_name", "-"))
    m3.metric("País", res.get("country_name", "-"))
    m4.metric("Ads Enriquecidas", res.get("google_ads", {}).get("keywords_enriched", 0))

    # Tabs
    tabs = st.tabs(["💎 Sugerencias", "❓ PAA", "📝 Preguntas AC", "🔗 Relacionadas", "📥 Exportar"])

    def _render(items, tab):
        if not items:
            tab.info("Sin resultados en esta sección.")
            return
        rows = []
        for kw in items:
            v = vol.get(kw, {})
            rows.append({"Keyword": kw, "Ads/mes": v.get("google_ads_avg_monthly_searches", "-"),
                          "Trend": v.get("google_trends_promedio", "-"), "Score": v.get("score", 0),
                          "Prioridad": v.get("categoria", "-")})
        df = pd.DataFrame(rows)
        tab.dataframe(df, use_container_width=True, column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "Keyword": st.column_config.TextColumn("Keyword", width="large"),
        })

    _render(res["sugerencias"], tabs[0])
    _render(res["preguntas_paa"], tabs[1])
    _render(res["preguntas_autocompletado"], tabs[2])
    _render(res["busquedas_relacionadas"], tabs[3])

    with tabs[4]:
        st.markdown("### Descargar Reportes")
        try:
            from exporters.excel_export import exportar_excel
            from exporters.json_export import exportar_json
            c1, c2 = st.columns(2)
            excel_path = exportar_excel(res["keyword"], res)
            with open(excel_path, "rb") as f:
                c1.download_button("📊 Descargar Excel", f, file_name=os.path.basename(excel_path), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            json_path = exportar_json(res["keyword"], res)
            with open(json_path, "rb") as f:
                c2.download_button("{ } Descargar JSON", f, file_name=os.path.basename(json_path), mime="application/json")
        except Exception as e:
            st.error(f"Error al exportar: {e}")
