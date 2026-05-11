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
from scraper.volume_estimator import estimar_volumenes
from scraper.google_ads_metrics import enrich_with_google_ads_metrics
from exporters.excel_export import exportar_excel
from exporters.json_export import exportar_json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title=f"KeySearch V 6.0 - Pipeline Hub",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ESTILOS CSS (BASADOS EN STITCH DESIGN SYSTEM) ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<style>
    /* Reset & Base */
    :root {
        --primary: #000000;
        --secondary: #00677f;
        --secondary-container: #00d2ff;
        --background: #f8f9ff;
        --surface: #f8f9ff;
        --on-surface: #0b1c30;
        --on-surface-variant: #44474d;
        --outline-variant: #c5c6cd;
        --surface-container-low: #eff4ff;
        --surface-container-lowest: #ffffff;
    }

    .stApp {
        background-color: var(--background);
    }

    [data-testid="stSidebar"] {
        background-color: var(--surface);
        border-right: 1px solid var(--outline-variant);
        width: 240px !important;
    }

    /* Typography */
    h1, h2, h3, p, span, div {
        font-family: 'Inter', sans-serif !important;
    }
    .mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Custom Header */
    .custom-header {
        position: fixed;
        top: 0;
        right: 0;
        height: 64px;
        width: 100%;
        background: var(--surface-container-lowest);
        border-bottom: 1px solid var(--outline-variant);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 24px;
        z-index: 1000;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }

    /* Sidebar Logo */
    .sidebar-logo {
        padding: 24px 16px;
        margin-bottom: 32px;
    }
    .sidebar-logo h1 {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary);
        margin: 0;
    }
    .sidebar-logo p {
        font-size: 12px;
        color: var(--on-surface-variant);
        font-family: 'JetBrains Mono' !important;
        margin: 0;
    }

    /* Sidebar Nav */
    .nav-item {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 8px 16px;
        border-radius: 4px;
        color: var(--on-surface-variant);
        text-decoration: none;
        transition: all 0.2s;
        margin-bottom: 4px;
        cursor: pointer;
    }
    .nav-item:hover {
        background-color: #dce9ff;
    }
    .nav-item.active {
        color: var(--secondary);
        font-weight: 700;
        background-color: #e5eeff;
        border-right: 4px solid var(--secondary-container);
    }

    /* Cards */
    .ks-card {
        background: var(--surface-container-lowest);
        border: 1px solid var(--outline-variant);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 24px;
    }
    .pipeline-gradient {
        background: linear-gradient(135deg, #0d1c32 0%, #00677f 100%);
        color: white;
    }

    /* Tables */
    .ks-table {
        width: 100%;
        border-collapse: collapse;
    }
    .ks-table th {
        background: var(--surface-container-low);
        color: var(--on-surface-variant);
        font-family: 'JetBrains Mono' !important;
        font-size: 12px;
        text-transform: uppercase;
        padding: 12px 24px;
        text-align: left;
    }
    .ks-table td {
        padding: 16px 24px;
        border-bottom: 1px solid var(--outline-variant);
    }

    /* Buttons */
    .stButton>button {
        border-radius: 9999px !important;
        background-color: var(--primary) !important;
        color: white !important;
        border: none !important;
        padding: 8px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .stButton>button:hover {
        opacity: 0.9 !important;
        transform: scale(0.98);
    }

    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 2rem !important;}
</style>
""", unsafe_allow_html=True)

# --- ESTADO DE NAVEGACIÓN ---
if "page" not in st.session_state:
    st.session_state.page = "Pipeline Hub"

# --- SIDEBAR PERSONALIZADO ---
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-logo">
        <h1>KeySearch V 6.0</h1>
        <p>SEO Pipeline Engine</p>
    </div>
    """, unsafe_allow_html=True)
    
    pages = [
        {"name": "Pipeline Hub", "icon": "hub"},
        {"name": "Data Input", "icon": "input"},
        {"name": "Scraping", "icon": "database"},
        {"name": "IA Enrichment", "icon": "psychology"},
        {"name": "Export", "icon": "download"},
    ]
    
    for p in pages:
        active_class = "active" if st.session_state.page == p["name"] else ""
        if st.markdown(f"""
        <div class="nav-item {active_class}">
            <span class="material-symbols-outlined">{p['icon']}</span>
            <span class="mono">{p['name']}</span>
        </div>
        """, unsafe_allow_html=True):
            # Nota: Esto es solo visual, los clicks en markdown no cambian el estado de Streamlit directamente
            # Usaremos un radio oculto o botones reales para la navegación funcional
            pass
    
    st.divider()
    
    # Navegación funcional (oculta visualmente para mantener el diseño)
    st.session_state.page = st.radio(
        "Navegación",
        options=[p["name"] for p in pages],
        label_visibility="collapsed",
        index=0
    )
    
    st.markdown("""<div style="margin-top: auto; border-top: 1px solid var(--outline-variant); padding-top: 16px;">""", unsafe_allow_html=True)
    if st.button("New Project"):
        st.toast("Nuevo proyecto iniciado")
    
    st.markdown("""
        <div class="nav-item">
            <span class="material-symbols-outlined">settings</span>
            <span class="mono">Settings</span>
        </div>
        <div class="nav-item">
            <span class="material-symbols-outlined">menu_book</span>
            <span class="mono">Docs</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- HEADER PERSONALIZADO ---
st.markdown(f"""
<div class="custom-header">
    <div style="display: flex; gap: 32px; align-items: center;">
        <h2 style="font-size: 20px; font-weight: 600; color: var(--primary); margin: 0;">{st.session_state.page}</h2>
    </div>
    <div style="display: flex; gap: 24px; align-items: center;">
        <div style="position: relative;">
            <input type="text" placeholder="Search data..." style="background: var(--surface-container-low); border: 1px solid var(--outline-variant); border-radius: 9999px; padding: 4px 16px; font-size: 14px; width: 240px;">
        </div>
        <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuDz564SCf6e6f7klfOsVf3FBotBz5jcLwzPcBi_1--d59GM2VzuiZzAw0ZrC3oI_7FACuIWLC6_5UyJZn78d6MdKT-0GzQOzjONlhQoLyQfdsCvmAfCW34MEDUD3RlQpIBjcEiVolcbF_sBwapiBZPqlVF0to9i9XcvgeYktOYlSjfgVUzozTHxC0KlSQzlqZ9BqhAhnIO9NhM0JGHakNPzRlj0102IIhPCbWly6KgadNRvQ0tMgXiUpNFHxImabV-tVUlOplbVKC8r" style="width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--outline-variant);">
    </div>
</div>
""", unsafe_allow_html=True)

# Espaciador para el header fijo
st.markdown("<br><br>", unsafe_allow_html=True)

# --- LÓGICA DE PÁGINAS ---

if st.session_state.page == "Pipeline Hub":
    # Stats Row
    col1, col2, col3 = st.columns([1.5, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="ks-card pipeline-gradient">
            <span class="mono" style="text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.8; font-size: 12px;">System Health</span>
            <h3 style="font-size: 32px; margin: 8px 0;">Optimal Performance</h3>
            <p style="opacity: 0.9; font-size: 14px;">Global SEO nodes are active across 12 clusters. All data pipes are running within nominal latency bounds.</p>
            <div style="margin-top: 32px; display: flex; align-items: center; gap: 12px;">
                <div style="background: #10b981; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span class="material-symbols-outlined" style="font-size: 18px;">check</span>
                </div>
                <span class="mono" style="font-size: 12px;">Active Nodes (42/42)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="ks-card">
            <p class="mono" style="color: var(--on-surface-variant); font-size: 14px; margin-bottom: 4px;">Processed Keywords</p>
            <h2 style="font-size: 48px; font-weight: 700; margin: 0;">1.2M</h2>
            <div style="margin-top: 24px;">
                <div style="width: 100%; background: var(--surface-container-low); height: 4px; border-radius: 9999px; overflow: hidden;">
                    <div style="background: var(--secondary-container); height: 100%; width: 78%;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                    <span class="mono" style="font-size: 12px; color: var(--on-surface-variant);">Target: 1.5M</span>
                    <span class="mono" style="font-size: 12px; color: var(--secondary); font-weight: 700;">+12.4%</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="ks-card">
            <p class="mono" style="color: var(--on-surface-variant); font-size: 14px; margin-bottom: 4px;">Success Rate</p>
            <h2 style="font-size: 48px; font-weight: 700; margin: 0;">99.8%</h2>
            <div style="margin-top: 24px; height: 32px; display: flex; align-items: flex-end; gap: 4px;">
                <div style="flex: 1; background: var(--secondary); height: 50%; border-radius: 2px 2px 0 0;"></div>
                <div style="flex: 1; background: var(--secondary); height: 75%; border-radius: 2px 2px 0 0;"></div>
                <div style="flex: 1; background: var(--secondary); height: 60%; border-radius: 2px 2px 0 0;"></div>
                <div style="flex: 1; background: var(--secondary-container); height: 100%; border-radius: 2px 2px 0 0;"></div>
            </div>
            <p class="mono" style="font-size: 12px; color: var(--on-surface-variant); margin-top: 8px;">Last 7 days efficiency</p>
        </div>
        """, unsafe_allow_html=True)

    # Pipeline Status
    st.markdown("""
    <div class="ks-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 16px 24px; border-bottom: 1px solid var(--outline-variant); display: flex; justify-content: space-between; align-items: center;">
            <h3 style="font-size: 18px; font-weight: 600; margin: 0;">SEO_Global_Enrichment_v2</h3>
            <span style="background: #d1fae5; color: #065f46; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                <div style="width: 8px; height: 8px; background: #10b981; border-radius: 50%;"></div> Running
            </span>
        </div>
        <div style="padding: 24px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <div style="width: 48px; height: 48px; background: var(--secondary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span class="material-symbols-outlined">input</span>
                </div>
                <span class="mono" style="font-size: 12px;">Ingestion</span>
            </div>
            <div style="flex: 1; height: 2px; background: var(--secondary); margin: 0 16px;"></div>
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <div style="width: 48px; height: 48px; background: var(--secondary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span class="material-symbols-outlined">database</span>
                </div>
                <span class="mono" style="font-size: 12px;">Scraping</span>
            </div>
            <div style="flex: 1; height: 2px; border-top: 2px dashed var(--outline-variant); margin: 0 16px;"></div>
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; opacity: 0.5;">
                <div style="width: 48px; height: 48px; border: 2px solid var(--outline-variant); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span class="material-symbols-outlined">psychology</span>
                </div>
                <span class="mono" style="font-size: 12px;">IA Enrichment</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # History Table
    st.markdown("""
    <div class="ks-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 16px 24px; border-bottom: 1px solid var(--outline-variant); display: flex; justify-content: space-between; align-items: center; background: #f1f5f9;">
            <h3 style="font-size: 18px; font-weight: 600; margin: 0;">Execution History</h3>
            <span style="color: var(--secondary); font-size: 14px; font-weight: 600; cursor: pointer;">View All →</span>
        </div>
        <table class="ks-table">
            <thead>
                <tr>
                    <th>Pipeline ID</th>
                    <th>Start Time</th>
                    <th>Volume</th>
                    <th>Status</th>
                    <th style="text-align: right;">Action</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><span class="mono" style="font-weight: 700;">KS-RUN-8821</span></td>
                    <td><div style="font-size: 14px;">2023-10-24</div><div style="font-size: 12px; color: var(--on-surface-variant);">14:32:01 UTC</div></td>
                    <td><span class="mono">245,000 req</span></td>
                    <td><span style="background: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">SUCCESS</span></td>
                    <td style="text-align: right;"><span class="material-symbols-outlined" style="color: var(--on-surface-variant); cursor: pointer;">visibility</span></td>
                </tr>
                <tr>
                    <td><span class="mono" style="font-weight: 700;">KS-RUN-8820</span></td>
                    <td><div style="font-size: 14px;">2023-10-24</div><div style="font-size: 12px; color: var(--on-surface-variant);">11:15:44 UTC</div></td>
                    <td><span class="mono">12,400 req</span></td>
                    <td><span style="background: #ffdad6; color: #93000a; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">FAILED</span></td>
                    <td style="text-align: right;"><span class="material-symbols-outlined" style="color: var(--on-surface-variant); cursor: pointer;">visibility</span></td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == "Data Input":
    # Formulario de configuración
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <h2 style="font-size: 32px; font-weight: 600; margin: 0;">Configuración de Búsqueda</h2>
        <p style="color: var(--on-surface-variant); margin-top: 8px;">Define los parámetros de entrada para la extracción y enriquecimiento de datos SEO.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Keyword Input
        st.markdown("""
        <div class="ks-card">
            <div style="display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--outline-variant); padding-bottom: 16px; margin-bottom: 24px;">
                <span class="material-symbols-outlined" style="color: var(--secondary);">key</span>
                <h3 style="font-size: 20px; font-weight: 600; margin: 0;">Palabras Clave (Keywords)</h3>
            </div>
            <p style="font-size: 14px; font-weight: 600; margin-bottom: 4px;">Ingresar Keywords</p>
            <p style="font-size: 14px; color: var(--on-surface-variant); margin-bottom: 16px;">Introduce una keyword por línea o separadas por comas.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Area de texto real de Streamlit (posicionada sobre el card visual)
        keywords_raw = st.text_area(
            "Keywords",
            height=250,
            placeholder="ej: mejores herramientas seo 2024\nanalisis de competencia python\nautomatizacion marketing b2b",
            label_visibility="collapsed"
        )
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            # Segmentación
            st.markdown("""
            <div class="ks-card">
                <div style="display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--outline-variant); padding-bottom: 8px; margin-bottom: 16px;">
                    <span class="material-symbols-outlined" style="color: var(--secondary);">public</span>
                    <h3 style="font-size: 18px; font-weight: 600; margin: 0;">Segmentación</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            country_code = st.selectbox(
                "País de Búsqueda",
                options=list(COUNTRY_CATALOG.keys()),
                format_func=lambda x: f"{COUNTRY_CATALOG[x]['name']} ({x.upper()})"
            )
            
            st.radio("Idioma Principal", ["Español", "Inglés"], horizontal=True)
            
        with col_c2:
            # Perfil
            st.markdown("""
            <div class="ks-card">
                <div style="display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--outline-variant); padding-bottom: 8px; margin-bottom: 16px;">
                    <span class="material-symbols-outlined" style="color: var(--secondary);">settings_account_box</span>
                    <h3 style="font-size: 18px; font-weight: 600; margin: 0;">Perfil de Búsqueda</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            profile_choice = st.radio(
                "Agente de Extracción",
                options=["normal", "extreme"],
                format_func=lambda x: "Desktop (Chrome/MacOS)" if x == "normal" else "Deep Scan (Extreme Mode)"
            )

    with col_right:
        # Validation Card
        st.markdown("""
        <div class="ks-card" style="background: var(--primary); color: white; border: none; position: relative; overflow: hidden;">
            <div style="position: absolute; right: -40px; top: -40px; width: 160px; height: 160px; background: rgba(0,210,255,0.1); border-radius: 50%; filter: blur(30px);"></div>
            <h3 style="font-size: 20px; font-weight: 600; margin-bottom: 24px; position: relative; z-index: 1;">Validación del Proyecto</h3>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 12px;">
                <span style="opacity: 0.8; font-size: 14px;">Keywords detectadas</span>
                <span class="mono" style="color: var(--secondary-container); font-weight: 700;">Listas</span>
            </div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 12px;">
                <span style="opacity: 0.8; font-size: 14px;">Segmentación</span>
                <span class="mono" style="color: var(--secondary-container); font-weight: 700;">Lista</span>
            </div>
            <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.2);">
                <p class="mono" style="text-transform: uppercase; font-size: 10px; opacity: 0.6; margin-bottom: 4px;">Consumo Estimado</p>
                <div style="display: flex; align-items: baseline; gap: 8px;">
                    <span style="font-size: 32px; font-weight: 700;">450</span>
                    <span style="font-size: 18px; opacity: 0.7;">Créditos</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        run_btn = st.button("🚀 INICIAR PIPELINE", use_container_width=True)
        
        if run_btn:
            st.success("Pipeline iniciado correctamente")

else:
    # Placeholder para otras páginas
    st.info(f"Página {st.session_state.page} en desarrollo para coincidir con el diseño.")

# --- FOOTER / FLOATING ACTIONS ---
st.markdown("""
<div style="position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; gap: 12px; z-index: 1000;">
    <div style="width: 56px; height: 56px; background: white; border: 1px solid var(--outline-variant); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); cursor: pointer;">
        <span class="material-symbols-outlined">chat</span>
    </div>
    <div style="width: 56px; height: 56px; background: var(--secondary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.2); cursor: pointer;">
        <span class="material-symbols-outlined">save</span>
    </div>
</div>
""", unsafe_allow_html=True)
