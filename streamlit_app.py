import streamlit as st
import pandas as pd
import os
import sys
import time
from datetime import datetime

# Añadir el directorio actual al path para importar módulos locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_NAME, APP_VERSION, GROQ_API_KEY, SCRAPE_PROFILE, COUNTRY_CATALOG, normalize_country
from scraper.categorizer import auto_categorizar
from scraper.autocomplete import get_autocomplete_suggestions, get_question_suggestions
from scraper.google_serp import scrape_google
from scraper.volume_estimator import estimar_volumenes, ordenar_por_volumen
from scraper.google_ads_metrics import enrich_with_google_ads_metrics
from exporters.excel_export import exportar_excel
from exporters.json_export import exportar_json

# Configuración de la página
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos personalizados (Premium Dark Mode)
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a, #020617);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #3b82f6;
        color: white;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2563eb;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.5);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
    }
    .category-tag {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: bold;
    }
    .high-score { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }
    .mid-score { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }
    .low-score { background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #3b82f6; }
    
    /* Animaciones suaves */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
        animation: fadeIn 0.5s ease-out forwards;
    }
</style>
""", unsafe_allow_html=True)

def get_score_class(score):
    if score >= 80: return "high-score"
    if score >= 55: return "mid-score"
    return "low-score"

def process_keyword(keyword, country_code, profile):
    # Contexto de búsqueda
    country_data = normalize_country(country_code)
    search_context = {
        "country_code": country_data["country_code"],
        "country_name": country_data["country_name"],
        "language_code": country_data["language_code"],
        "google_ads_geo_targets": country_data["google_ads_geo_targets"],
        "scrape_profile": profile
    }
    
    # Categorización automática
    categoria, subcategoria = auto_categorizar(keyword)
    editorial_context = {
        "category_name": categoria,
        "subcategory_name": subcategoria,
    }
    
    results = {
        "keyword": keyword,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "country": country_data["country_name"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 1. Sugerencias de autocompletado
    status = st.status(f"Analizando: **{keyword}**", expanded=True)
    
    status.write("🔍 Obteniendo sugerencias de autocompletado...")
    sugerencias = get_autocomplete_suggestions(keyword, expandir=True, search_context=search_context)
    results["sugerencias"] = sugerencias
    
    status.write("❓ Generando preguntas por autocompletado...")
    preguntas_ac = get_question_suggestions(keyword, search_context=search_context)
    results["preguntas_autocompletado"] = preguntas_ac
    
    status.write("🌐 Extrayendo datos de la SERP (PAA y Relacionadas)...")
    serp_data = scrape_google(keyword, search_context=search_context)
    results["preguntas_paa"] = serp_data.get("preguntas_paa", [])
    results["busquedas_relacionadas"] = serp_data.get("busquedas_relacionadas", [])
    
    # 2. Filtrado IA (si está habilitado)
    if GROQ_API_KEY:
        status.write("🤖 Filtrando con IA (Groq)...")
        from scraper.ai_filter import filtrar_con_ia
        
        def _filter(items, name):
            if not items: return items
            return filtrar_con_ia(items, keyword, search_context["country_name"])
            
        results["sugerencias"] = _filter(results["sugerencias"], "sugerencias")
        results["preguntas_autocompletado"] = _filter(results["preguntas_autocompletado"], "preguntas ac")
        results["preguntas_paa"] = _filter(results["preguntas_paa"], "preguntas PAA")
        results["busquedas_relacionadas"] = _filter(results["busquedas_relacionadas"], "relacionadas")
    
    # 3. Métricas y Estimaciones
    status.write("📊 Analizando señales reales de Google...")
    volumenes = estimar_volumenes(
        keyword_principal=keyword,
        sugerencias=results["sugerencias"],
        preguntas_paa=results["preguntas_paa"],
        preguntas_autocompletado=results["preguntas_autocompletado"],
        busquedas_relacionadas=results["busquedas_relacionadas"],
        usar_trends=True,
        metadata={
            "categoria_padre": categoria,
            "subcategoria": subcategoria,
            "referencia": keyword,
            "pais": search_context["country_name"],
            "pais_codigo": search_context["country_code"],
            "google_ads_geo_targets": search_context["google_ads_geo_targets"],
        },
        search_context=search_context
    )
    
    status.write("💰 Enriqueciendo con Google Ads API...")
    google_ads_result = enrich_with_google_ads_metrics(volumenes)
    results["volumenes"] = volumenes
    results["google_ads"] = google_ads_result
    
    status.update(label="✅ Análisis completado", state="complete", expanded=False)
    
    return results

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png", width=150) # Placeholder for logo
    st.title(f"🚀 {APP_NAME}")
    st.caption(f"Versión {APP_VERSION}")
    
    st.divider()
    
    keyword_input = st.text_input("Palabra clave semilla", placeholder="ej. marketing digital")
    
    country_code = st.selectbox(
        "País de análisis",
        options=list(COUNTRY_CATALOG.keys()),
        format_func=lambda x: f"{COUNTRY_CATALOG[x]['name']} ({x.upper()})",
        index=0
    )
    
    profile = st.radio(
        "Perfil de extracción",
        options=["normal", "extreme"],
        format_func=lambda x: "Normal (Equilibrado)" if x == "normal" else "Extreme (Máxima cobertura)",
        help="El modo extreme realiza más peticiones y es más profundo."
    )
    
    analyze_btn = st.button("🚀 Iniciar Investigación")
    
    st.divider()
    
    if GROQ_API_KEY:
        st.success("✅ IA Groq Conectada")
    else:
        st.warning("⚠️ Sin Groq API Key (Filtro IA omitido)")
        
    if os.path.exists("google-ads.yaml"):
        st.success("✅ Google Ads API Lista")
    else:
        st.info("ℹ️ Usando solo señales de tendencias")

# --- MAIN CONTENT ---
if analyze_btn and keyword_input:
    with st.spinner("Investigando mercado..."):
        results = process_keyword(keyword_input, country_code, profile)
        st.session_state["results"] = results

if "results" in st.session_state:
    res = st.session_state["results"]
    
    # Header de resultados
    st.header(f"Resultados: {res['keyword']}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Keywords", len(res["volumenes"]))
    with col2:
        st.metric("Categoría", res["categoria"])
    with col3:
        st.metric("Subcategoría", res["subcategoria"])
    with col4:
        st.metric("Ads Enriquecidas", res["google_ads"].get("keywords_enriched", 0))
    
    st.divider()
    
    # Tabs para visualizar datos
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💎 Sugerencias", 
        "❓ Preguntas PAA", 
        "📝 Preguntas Autocompletado", 
        "🔗 Relacionadas",
        "📥 Exportar"
    ])
    
    def render_table(keywords):
        if not keywords:
            st.info("No se encontraron resultados para esta sección.")
            return
            
        data = []
        for kw in keywords:
            vol = res["volumenes"].get(kw, {})
            score = vol.get("score", 0)
            ads = vol.get("google_ads_avg_monthly_searches", "-")
            trend = vol.get("google_trends_promedio", "-")
            
            data.append({
                "Keyword": kw,
                "Ads/mes": ads,
                "Trend (0-100)": trend,
                "Score": score,
                "Prioridad": vol.get("categoria", "-")
            })
            
        df = pd.DataFrame(data)
        st.dataframe(
            df, 
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score",
                    min_value=0,
                    max_value=100,
                    format="%d"
                ),
                "Keyword": st.column_config.TextColumn("Keyword", width="large")
            }
        )

    with tab1:
        render_table(res["sugerencias"])
        
    with tab2:
        render_table(res["preguntas_paa"])
        
    with tab3:
        render_table(res["preguntas_autocompletado"])
        
    with tab4:
        render_table(res["busquedas_relacionadas"])
        
    with tab5:
        st.subheader("Descargar Reportes")
        col_ex1, col_ex2 = st.columns(2)
        
        # Generar archivos para descargar
        excel_path = exportar_excel(res["keyword"], res)
        with open(excel_path, "rb") as f:
            col_ex1.download_button(
                "📊 Descargar Excel (.xlsx)",
                f,
                file_name=os.path.basename(excel_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        json_path = exportar_json(res["keyword"], res)
        with open(json_path, "rb") as f:
            col_ex2.download_button(
                "{ } Descargar JSON",
                f,
                file_name=os.path.basename(json_path),
                mime="application/json"
            )

else:
    # Estado inicial / Bienvenida
    st.info("👈 Ingresa una palabra clave en el panel lateral para comenzar la investigación.")
    
    col_hero1, col_hero2 = st.columns([2, 1])
    with col_hero1:
        st.markdown(f"""
        ### Descubre señales reales de demanda
        Esta herramienta extrae datos directamente de Google para identificar qué están buscando las personas realmente.
        
        - **Autocompletado Pro**: Expansión alfabética de términos.
        - **People Also Ask**: Preguntas reales extraídas de la SERP.
        - **Google Trends**: Validación de interés histórico.
        - **Google Ads**: Volumen de búsqueda mensual exacto.
        - **IA Groq**: Filtrado inteligente de ruido.
        """)
    with col_hero2:
        st.image("https://cdn-icons-png.flaticon.com/512/270/270021.png", width=200) # Search icon
