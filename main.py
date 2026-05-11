"""
KeySearch V 6.0 - Streamlit Web Interface
Versión de Alta Fidelidad (Stitch Design System)
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

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="KeySearch V 6.0 | SEO Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DESIGN SYSTEM & CSS ---
def inject_custom_styles():
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <style>
        /* CSS Variables based on DESIGN.md */
        :root {
            --surface: #f8f9ff;
            --on-surface: #0b1c30;
            --on-surface-variant: #44474d;
            --surface-container-lowest: #ffffff;
            --surface-container-low: #eff4ff;
            --surface-container: #e5eeff;
            --surface-container-high: #dce9ff;
            --outline-variant: #c5c6cd;
            --primary: #000000;
            --secondary: #00677f;
            --secondary-container: #00d2ff;
            --primary-container: #0d1c32;
            --on-primary-container: #76849f;
            --error: #ba1a1a;
            --error-container: #ffdad6;
            --on-error-container: #93000a;
        }

        /* Global Overrides */
        .stApp {
            background-color: var(--surface) !important;
            font-family: 'Inter', sans-serif !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: var(--surface-container-lowest) !important;
            border-right: 1px solid var(--outline-variant) !important;
            width: 260px !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0px !important;
        }
        
        /* Sidebar Logo/Header */
        .sidebar-header {
            padding: 24px 16px;
            border-bottom: 1px solid var(--outline-variant);
            margin-bottom: 24px;
        }
        .sidebar-header h1 {
            font-size: 24px !important;
            font-weight: 700 !important;
            color: var(--primary) !important;
            margin: 0 !important;
        }
        .sidebar-header p {
            font-family: 'JetBrains Mono' !important;
            font-size: 12px !important;
            color: var(--on-surface-variant) !important;
            margin: 0 !important;
        }

        /* Content Area */
        .block-container {
            padding: 2rem 4rem !important;
            max-width: 1400px !important;
        }

        /* Bento Cards */
        .ks-card {
            background: var(--surface-container-lowest);
            border: 1px solid var(--outline-variant);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s ease;
        }
        .ks-card:hover {
            transform: translateY(-2px);
        }
        
        .ks-gradient-card {
            background: linear-gradient(135deg, #0d1c32 0%, #00677f 100%);
            color: white;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }

        /* Typography */
        .mono { font-family: 'JetBrains Mono', monospace !important; }
        .text-h1 { font-size: 32px; font-weight: 600; letter-spacing: -0.01em; }
        .text-h2 { font-size: 24px; font-weight: 600; }
        .text-h3 { font-size: 20px; font-weight: 600; }
        .text-body-sm { font-size: 14px; color: var(--on-surface-variant); }
        .text-label-sm { font-family: 'JetBrains Mono'; font-size: 12px; font-weight: 500; text-transform: uppercase; }

        /* Metric styling */
        div[data-testid="stMetric"] {
            background: var(--surface-container-lowest);
            border: 1px solid var(--outline-variant);
            border-radius: 12px;
            padding: 16px 20px;
        }
        div[data-testid="stMetric"] label {
            font-family: 'JetBrains Mono' !important;
            font-size: 12px !important;
            color: var(--on-surface-variant) !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 32px !important;
            font-weight: 700 !important;
            color: var(--primary) !important;
        }

        /* Pipeline Stepper */
        .stepper-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 32px;
            background: var(--surface-container-lowest);
            border: 1px solid var(--outline-variant);
            border-radius: 12px;
            margin-top: 24px;
        }
        .step-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            flex: 1;
        }
        .step-circle {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        .step-done { background: #10b981; color: white; }
        .step-active { background: var(--secondary); color: white; box-shadow: 0 0 0 4px var(--secondary-container); animation: pulse 2s infinite; }
        .step-pending { border: 2px dashed var(--outline-variant); color: var(--on-surface-variant); }
        .step-line { flex: 1; height: 2px; margin: 0 16px; margin-top: -24px; }
        .line-done { background: #10b981; }
        .line-pending { border-top: 2px dashed var(--outline-variant); }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0px rgba(0, 210, 255, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(0, 210, 255, 0); }
            100% { box-shadow: 0 0 0 0px rgba(0, 210, 255, 0); }
        }

        /* Buttons and Inputs */
        .stButton button {
            background: var(--primary) !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            border: none !important;
            transition: all 0.2s !important;
        }
        .stButton button:hover {
            opacity: 0.9 !important;
            transform: scale(1.02) !important;
        }
        .stTextArea textarea {
            border-radius: 12px !important;
            border: 1px solid var(--outline-variant) !important;
            background-color: var(--surface-container-lowest) !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 14px !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            padding: 4px;
            background: var(--surface-container);
            border-radius: 12px;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: 8px;
            padding: 8px 16px;
            font-family: 'JetBrains Mono' !important;
            font-size: 13px !important;
        }
        .stTabs [aria-selected="true"] {
            background: white !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* Hide elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] { background: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

# --- COMPONENTS ---
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <h1>KeySearch V 6.0</h1>
            <p>SEO Pipeline Engine</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        st.markdown("<br>", unsafe_allow_html=True)
        nav = st.radio(
            "Navegación",
            ["🏠 Pipeline Hub", "📥 Data Input", "📊 Resultados", "⚙️ Configuración"],
            label_visibility="collapsed"
        )
        
        st.markdown("<div style='flex-grow:1'></div>", unsafe_allow_html=True)
        st.divider()
        
        # System Stats in Sidebar
        st.caption("ESTADO DE SERVICIOS")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""<div style='background:#dcfce7;color:#166534;padding:4px 8px;border-radius:4px;font-size:10px;font-weight:700;text-align:center'>API OK</div>""", unsafe_allow_html=True)
        with c2:
            st.markdown("""<div style='background:#fef9c3;color:#854d0e;padding:4px 8px;border-radius:4px;font-size:10px;font-weight:700;text-align:center'>SCRAPER IDLE</div>""", unsafe_allow_html=True)
            
        return nav

def render_pipeline_stepper(step=1):
    steps = [
        ("input", "Ingestion", "COMPLETE" if step > 1 else ("ACTIVE" if step == 1 else "PENDING")),
        ("database", "Scraping", "COMPLETE" if step > 2 else ("ACTIVE" if step == 2 else "PENDING")),
        ("psychology", "Enrichment", "COMPLETE" if step > 3 else ("ACTIVE" if step == 3 else "PENDING")),
        ("download", "Export", "COMPLETE" if step > 4 else ("ACTIVE" if step == 4 else "PENDING")),
    ]
    
    html = '<div class="stepper-container">'
    for i, (icon, label, status) in enumerate(steps):
        circle_class = "step-done" if status == "COMPLETE" else ("step-active" if status == "ACTIVE" else "step-pending")
        html += f"""
        <div class="step-item">
            <div class="step-circle {circle_class}">
                <span class="material-symbols-outlined">{icon}</span>
            </div>
            <div style="text-align:center">
                <div class="mono" style="font-size:12px;font-weight:600">{label}</div>
                <div class="mono" style="font-size:9px;opacity:0.7">{status}</div>
            </div>
        </div>
        """
        if i < len(steps) - 1:
            line_class = "line-done" if status == "COMPLETE" else "line-pending"
            html += f'<div class="step-line {line_class}"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# --- LAZY IMPORTS ---
def _safe_import():
    mods = {}
    try:
        from config import APP_VERSION, COUNTRY_CATALOG, normalize_country, GROQ_API_KEY
        mods.update({"APP_VERSION": APP_VERSION, "COUNTRY_CATALOG": COUNTRY_CATALOG, "normalize_country": normalize_country, "GROQ_API_KEY": GROQ_API_KEY})
    except Exception:
        mods.update({"APP_VERSION": "6.0", "COUNTRY_CATALOG": {"co": {"name": "Colombia"}, "mx": {"name": "Mexico"}}, "normalize_country": lambda x: {"country_code": x, "country_name": x, "language_code": "es", "google_ads_geo_targets": []}, "GROQ_API_KEY": os.getenv("GROQ_API_KEY", "")})
    return mods

MODS = _safe_import()

# --- APP LAYOUT ---
inject_custom_styles()
nav_choice = render_sidebar()

if nav_choice == "🏠 Pipeline Hub":
    st.markdown("<h2 class='text-h1'>Pipeline Hub</h2>", unsafe_allow_html=True)
    st.markdown("<p class='text-body-sm'>Estado global del motor de extracción y señales de demanda.</p>", unsafe_allow_html=True)
    
    # Bento Grid
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        st.markdown("""
        <div class="ks-gradient-card">
            <span class="text-label-sm" style="opacity:0.8">SYSTEM HEALTH</span>
            <h3 class="text-h1" style="color:white;margin:8px 0">Rendimiento Óptimo</h3>
            <p style="font-size:14px;opacity:0.9;line-height:1.6">
                Todos los nodos de extracción están operativos. Latencia actual: 142ms. 
                El motor de IA (Groq) está listo para el enriquecimiento.
            </p>
            <div style="margin-top:24px;display:flex;align-items:center;gap:12px">
                <div style="background:rgba(255,255,255,0.1);padding:8px 16px;border-radius:99px;font-size:12px;font-family:JetBrains Mono">
                    Uptime: 99.98%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        st.metric("Keywords Procesadas", "1.2M", "+12.4%")
        st.markdown("<br>", unsafe_allow_html=True)
        st.metric("Success Rate", "99.8%", "0.2%")

    with c3:
        st.markdown("""
        <div class="ks-card" style="height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center">
            <span class="material-symbols-outlined" style="font-size:48px;color:var(--secondary);margin-bottom:12px">tips_and_updates</span>
            <div class="mono" style="font-size:14px;font-weight:700">IA INSIGHT</div>
            <p class='text-body-sm' style='margin-top:8px'>Latencia en EU-West +15%. Reequilibrar nodos.</p>
        </div>
        """, unsafe_allow_html=True)

    # Pipeline Stepper
    st.markdown("<h3 class='text-h3' style='margin-top:32px'>Pipeline Actual</h3>", unsafe_allow_html=True)
    render_pipeline_stepper(step=1)
    
    # Recent Projects (Simulation)
    st.markdown("<h3 class='text-h3' style='margin-top:32px'>Historial de Ejecución</h3>", unsafe_allow_html=True)
    hist_data = pd.DataFrame([
        {"ID": "KS-RUN-8821", "Iniciado": "Hace 2h", "Keywords": 245, "Estado": "Completado"},
        {"ID": "KS-RUN-8820", "Iniciado": "Hace 5h", "Keywords": 12, "Estado": "Error"},
        {"ID": "KS-RUN-8819", "Iniciado": "Ayer", "Keywords": 1200, "Estado": "Completado"},
    ])
    st.dataframe(hist_data, use_container_width=True)

elif nav_choice == "📥 Data Input":
    st.markdown("<h2 class='text-h1'>Configuración de Búsqueda</h2>", unsafe_allow_html=True)
    st.markdown("<p class='text-body-sm'>Define los parámetros de entrada para la extracción masiva.</p>", unsafe_allow_html=True)
    
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        with st.container(border=True):
            st.markdown("<h3 class='text-h3'><span class='material-symbols-outlined' style='vertical-align:middle;margin-right:8px'>key</span>Palabras Clave</h3>", unsafe_allow_html=True)
            keywords_text = st.text_area(
                "Una por línea o separadas por comas",
                height=300,
                placeholder="ej: mejores herramientas seo 2024\nanalisis competencia\n..."
            )
            kw_list = [k.strip() for k in keywords_text.replace("\n", ",").split(",") if k.strip()]
            st.markdown(f"<div class='mono' style='font-size:12px;opacity:0.6;margin-top:8px'>{len(kw_list)} / 500 keywords detectadas</div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("<h3 class='text-h3'><span class='material-symbols-outlined' style='vertical-align:middle;margin-right:8px'>public</span>Segmentación</h3>", unsafe_allow_html=True)
                country = st.selectbox("País", options=list(MODS["COUNTRY_CATALOG"].keys()), format_func=lambda x: f"{MODS['COUNTRY_CATALOG'][x]['name']} ({x.upper()})")
                lang = st.radio("Idioma", ["Español", "Inglés"], horizontal=True)
        with c2:
            with st.container(border=True):
                st.markdown("<h3 class='text-h3'><span class='material-symbols-outlined' style='vertical-align:middle;margin-right:8px'>settings_account_box</span>Perfil</h3>", unsafe_allow_html=True)
                profile = st.radio("Agente", ["Desktop (Chrome)", "Mobile (Safari)", "Deep Scan"], index=0)

    with col_side:
        # Project Validation
        st.markdown(f"""
        <div class="ks-card" style="background:var(--primary-container);color:white;border:none">
            <h3 class="text-h2" style="color:white;margin-bottom:24px">Validación</h3>
            <div style="display:flex;justify-content:space-between;margin-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:8px">
                <span style="opacity:0.8">Keywords</span>
                <span class="mono" style="color:var(--secondary-container)">{"LISTO" if kw_list else "PENDIENTE"}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:24px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:8px">
                <span style="opacity:0.8">Proxies</span>
                <span class="mono" style="color:#10b981">ACTIVO</span>
            </div>
            <div style="margin-top:32px">
                <div class="text-label-sm" style="opacity:0.6">Consumo Estimado</div>
                <div class="text-h1" style="color:white">{len(kw_list)*10 if kw_list else 0} <span style="font-size:16px;font-weight:400;opacity:0.7">Créditos</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 INICIAR PIPELINE", use_container_width=True):
            if not kw_list:
                st.error("Ingresa keywords.")
            else:
                st.session_state["running"] = True
                st.rerun()

elif nav_choice == "📊 Resultados":
    if "results" not in st.session_state or not st.session_state["results"]:
        st.info("No hay datos. Ejecuta un análisis en **Data Input**.")
        st.stop()
    
    # ... render results with nice tables ...
    st.markdown("<h2 class='text-h1'>Resultados</h2>", unsafe_allow_html=True)
    # (Similar logic to previous version but with better styling)

# --- EXECUTION LOGIC (MOCK FOR UI DEMO) ---
if st.session_state.get("running"):
    st.markdown("<h2 class='text-h1'>Ejecutando Pipeline...</h2>", unsafe_allow_html=True)
    render_pipeline_stepper(step=2)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(101):
        time.sleep(0.05)
        progress_bar.progress(i)
        status_text.markdown(f"<div class='mono' style='font-size:12px;text-align:center'>Procesando: {i}% completado</div>", unsafe_allow_html=True)
    
    st.session_state["running"] = False
    st.success("Análisis completado satisfactoriamente.")
    # Here you would actually call the backend scrapers
