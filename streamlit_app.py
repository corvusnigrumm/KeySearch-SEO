import streamlit as st
import pandas as pd
import os
import sys
import time
from datetime import datetime

# Añadir el directorio actual al path para importar módulos locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_NAME, APP_VERSION, COUNTRY_CATALOG, normalize_country
from scraper.categorizer import auto_categorizar
from scraper.autocomplete import get_autocomplete_suggestions, get_question_suggestions
from scraper.google_serp import scrape_google
from scraper.volume_estimator import estimar_volumenes
from scraper.google_ads_metrics import enrich_with_google_ads_metrics
from exporters.excel_export import exportar_excel
from exporters.json_export import exportar_json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title=f"KeySearch V 6.0",
    page_icon="🔍",
    layout="wide",
)

# --- ESTILOS CSS ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<style>
    :root {
        --primary: #000000;
        --secondary: #00677f;
        --secondary-container: #00d2ff;
        --background: #f8f9ff;
        --surface-container-lowest: #ffffff;
        --outline-variant: #c5c6cd;
        --on-surface-variant: #44474d;
    }

    .stApp {
        background-color: var(--background);
    }

    /* Ajuste para que el contenido sea visible */
    .block-container {
        padding-top: 4rem !important;
        max-width: 1200px !important;
    }

    .ks-card {
        background: white;
        border: 1px solid var(--outline-variant);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .pipeline-gradient {
        background: linear-gradient(135deg, #0d1c32 0%, #00677f 100%);
        color: white;
    }

    .custom-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 60px;
        background: white;
        border-bottom: 1px solid var(--outline-variant);
        display: flex;
        align-items: center;
        padding: 0 24px;
        z-index: 999;
    }
    
    .mono { font-family: 'JetBrains Mono', monospace !important; }
</style>
""", unsafe_allow_html=True)

# --- NAVEGACIÓN ---
with st.sidebar:
    st.title("KeySearch V 6.0")
    st.caption("SEO Pipeline Engine")
    st.divider()
    page = st.selectbox("Ir a:", ["Pipeline Hub", "Data Input", "Resultados"])

# --- HEADER ---
st.markdown(f"""
<div class="custom-header">
    <h2 style="font-size: 18px; margin: 0; font-weight: 600;">{page}</h2>
</div>
""", unsafe_allow_html=True)

# --- CONTENIDO ---

if page == "Pipeline Hub":
    st.markdown("### Estado del Sistema")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="ks-card pipeline-gradient"><h3>Optimal</h3><p>Nodes: 42/42</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ks-card"><h3>1.2M</h3><p>Keywords Processed</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="ks-card"><h3>99.8%</h3><p>Success Rate</p></div>', unsafe_allow_html=True)

elif page == "Data Input":
    st.markdown("### Configuración de Búsqueda")
    
    with st.container(border=True):
        keywords_raw = st.text_area("Keywords (una por línea)", height=200)
        
        col1, col2 = st.columns(2)
        with col1:
            country = st.selectbox("País", options=list(COUNTRY_CATALOG.keys()), format_func=lambda x: COUNTRY_CATALOG[x]['name'])
        with col2:
            profile = st.radio("Perfil", ["normal", "extreme"])
            
        if st.button("🚀 INICIAR PIPELINE"):
            if not keywords_raw:
                st.error("Por favor, ingresa al menos una keyword.")
            else:
                st.info("Iniciando análisis...")
                # Aquí iría la lógica de ejecución

else:
    st.info("Aquí se mostrarán los resultados una vez finalizado el proceso.")
