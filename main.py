"""
KeySearch V 6.0 - High Fidelity Stitch Design
Este archivo implementa la interfaz EXACTA del sistema de diseño Stitch.
"""
import streamlit as st
import pandas as pd
import os
import sys
import time
from datetime import datetime

# Path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="KeySearch V 6.0 | Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed" # We'll build our own sidebar
)

# --- THEME & CSS ---
def inject_stitch_styles():
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #000000; --secondary: #00677f; --secondary-container: #00d2ff;
            --background: #f8f9ff; --surface: #f8f9ff; --on-surface: #0b1c30;
            --on-surface-variant: #44474d; --outline-variant: #c5c6cd;
            --surface-container-low: #eff4ff; --surface-container-lowest: #ffffff;
            --surface-container: #e5eeff; --primary-container: #0d1c32;
            --on-primary-container: #76849f;
        }

        /* Hide Streamlit Native UI */
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        footer { visibility: hidden; }

        /* Custom Shell */
        .stitch-shell {
            display: flex;
            background-color: var(--background);
            min-height: 100vh;
        }

        /* Sidebar */
        .stitch-sidebar {
            width: 240px;
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            background: var(--surface);
            border-right: 1px solid var(--outline-variant);
            display: flex;
            flex-direction: column;
            padding: 24px 16px;
            z-index: 100;
        }
        .sidebar-brand h1 { font-family: 'Inter'; font-size: 24px; font-weight: 700; color: var(--primary); margin: 0; }
        .sidebar-brand p { font-family: 'JetBrains Mono'; font-size: 12px; color: var(--on-surface-variant); margin-top: 4px; }
        
        .nav-item {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 10px 16px;
            border-radius: 8px;
            text-decoration: none;
            color: var(--on-surface-variant);
            font-family: 'JetBrains Mono';
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
            cursor: pointer;
            margin-bottom: 4px;
        }
        .nav-item:hover { background: var(--surface-container-high); }
        .nav-item.active {
            background: var(--surface-container);
            color: var(--secondary);
            font-weight: 700;
            border-right: 4px solid var(--secondary-container);
        }
        .nav-item .material-symbols-outlined { font-size: 20px; }

        .sidebar-footer { margin-top: auto; border-top: 1px solid var(--outline-variant); pt-24px; }
        .btn-new-project {
            width: 100%;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            font-family: 'JetBrains Mono';
            font-weight: 700;
            margin: 24px 0;
            cursor: pointer;
        }

        /* Header */
        .stitch-header {
            position: fixed;
            top: 0;
            right: 0;
            left: 240px;
            height: 64px;
            background: var(--surface-container-lowest);
            border-bottom: 1px solid var(--outline-variant);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            z-index: 90;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .header-nav { display: flex; gap: 24px; }
        .header-nav a { font-family: 'Inter'; font-size: 15px; font-weight: 600; color: var(--on-surface-variant); text-decoration: none; padding-bottom: 16px; }
        .header-nav a.active { color: var(--primary); border-bottom: 2px solid var(--secondary); }

        .search-box {
            background: var(--surface-container-low);
            border: 1px solid var(--outline-variant);
            border-radius: 99px;
            padding: 6px 16px;
            width: 280px;
            font-size: 13px;
            display: flex;
            align-items: center;
        }
        .btn-run-pipeline {
            background: var(--primary);
            color: white;
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            margin-left: 12px;
        }

        /* Main Content */
        .stitch-main {
            margin-left: 240px;
            margin-top: 64px;
            padding: 32px;
            flex-grow: 1;
        }

        /* Cards and Grid */
        .bento-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 24px; }
        .card { background: var(--surface-container-lowest); border: 1px solid var(--outline-variant); border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        
        .gradient-card {
            background: linear-gradient(135deg, #0d1c32 0%, #00677f 100%);
            color: white;
            border-radius: 12px;
            padding: 32px;
        }
        .stat-value { font-size: 48px; font-weight: 700; margin: 8px 0; }
        
        /* Table */
        .data-table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        .data-table th { background: var(--surface-container-low); text-align: left; padding: 12px 16px; font-family: 'JetBrains Mono'; font-size: 12px; color: var(--on-surface-variant); text-transform: uppercase; }
        .data-table td { padding: 16px; border-bottom: 1px solid var(--outline-variant); font-size: 14px; }
        .tag-success { background: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
        
        /* Insight Card */
        .insight-card { border-left: 4px solid var(--secondary); }
        .btn-outline { border: 1px solid var(--secondary); color: var(--secondary); background: transparent; width: 100%; padding: 8px; border-radius: 4px; font-weight: 600; cursor: pointer; }
        
        /* Dark Card */
        .dark-card { background: var(--primary-container); color: white; position: relative; overflow: hidden; }
        .bolt-icon { position: absolute; bottom: -20px; right: -20px; font-size: 120px; opacity: 0.1; transform: rotate(15deg); }

        /* Material Symbols Helper */
        .material-symbols-outlined { font-size: 20px; vertical-align: middle; }
    </style>
    """, unsafe_allow_html=True)

# --- APP LOGIC ---
if "page" not in st.session_state:
    st.session_state.page = "Pipeline Hub"

inject_stitch_styles()

# 1. Custom Sidebar
st.markdown(f"""
<div class="stitch-sidebar">
    <div class="sidebar-brand">
        <h1>KeySearch V 6.0</h1>
        <p>SEO Pipeline Engine</p>
    </div>
    <div style="margin-top: 32px;">
        <div class="nav-item {"active" if st.session_state.page == "Pipeline Hub" else ""}" onclick="window.parent.postMessage({{type: 'streamlit:set_widget_value', key: 'page_nav', value: 'Pipeline Hub'}}, '*')">
            <span class="material-symbols-outlined">hub</span>
            <span>Pipeline Hub</span>
        </div>
        <div class="nav-item {"active" if st.session_state.page == "Data Input" else ""}">
            <span class="material-symbols-outlined">input</span>
            <span>Data Input</span>
        </div>
        <div class="nav-item">
            <span class="material-symbols-outlined">database</span>
            <span>Scraping</span>
        </div>
        <div class="nav-item">
            <span class="material-symbols-outlined">psychology</span>
            <span>IA Enrichment</span>
        </div>
        <div class="nav-item">
            <span class="material-symbols-outlined">download</span>
            <span>Export</span>
        </div>
    </div>
    <div class="sidebar-footer">
        <button class="btn-new-project">New Project</button>
        <div class="nav-item">
            <span class="material-symbols-outlined">settings</span>
            <span>Settings</span>
        </div>
        <div class="nav-item">
            <span class="material-symbols-outlined">menu_book</span>
            <span>Docs</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Use a hidden radio to handle navigation from Python if needed
# (Real interactivity between custom HTML and Streamlit requires some tricks, 
# for now we'll use standard Streamlit sidebar but hidden visually to sync state)
with st.sidebar:
    st.session_state.page = st.radio("Nav", ["Pipeline Hub", "Data Input", "Resultados"], label_visibility="hidden", key="page_nav")

# 2. Custom Header
st.markdown(f"""
<div class="stitch-header">
    <div class="header-nav">
        <a href="#" class="active">Dashboard</a>
        <a href="#">API Status</a>
        <a href="#">Logs</a>
    </div>
    <div style="display: flex; align-items: center;">
        <div class="search-box">
            <span class="material-symbols-outlined" style="opacity: 0.5; margin-right: 8px;">search</span>
            <span>Search data...</span>
        </div>
        <button class="btn-run-pipeline">Run Pipeline</button>
        <div style="margin-left: 16px; display: flex; align-items: center; gap: 12px;">
            <span class="material-symbols-outlined" style="color: var(--on-surface-variant)">notifications</span>
            <div style="width: 32px; height: 32px; background: #ddd; border-radius: 50%; overflow: hidden;">
                <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuC1YqIiqrnHjHr-wxFodqEQFPPv3zNmRX8Rh25ZaVX1WCkIIWBoIlXvmzqOYw8eeHzirLmYv2a4_4CnmXYUq4O_lqW2O-hwRwHiMGQRv04GFbFlBrZNDdBc3O7TXbCuJc5iBaB42g5AozN_UvomMO_c_UQD8Li59-krb8zl7RIBzUBn7GbiXGi3tYSlfFAxBAvLYgtt-ttbtkBteQFsYv1vb27FvcFx6K3gzcV8gaoaiKXL4lxmlo4L4A7ZB97aBGcQZpwqHt9BCDX3" style="width: 100%; height: 100%; object-fit: cover;">
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 3. Main Content
st.markdown("<div class='stitch-main'>", unsafe_allow_html=True)

if st.session_state.page == "Pipeline Hub":
    # Top Stats Row
    st.markdown("""
    <div class="bento-grid">
        <div class="gradient-card" style="grid-column: span 4;">
            <div class="text-label-sm" style="opacity: 0.8;">System Health</div>
            <div class="text-h1" style="color: white; margin: 12px 0;">Optimal Performance</div>
            <p style="font-size: 14px; opacity: 0.9; line-height: 1.6;">Global SEO nodes are active across 12 clusters. All data pipes are running within nominal latency bounds.</p>
            <div style="margin-top: 24px; display: flex; align-items: center; gap: 12px;">
                <span class="material-symbols-outlined" style="color: #10b981;">check_circle</span>
                <span class="mono" style="font-size: 12px;">Active Nodes (42/42)</span>
            </div>
        </div>
        <div class="card" style="grid-column: span 4;">
            <div style="display: flex; justify-content: space-between;">
                <span class="text-label-sm">Processed Keywords</span>
                <span class="material-symbols-outlined" style="color: var(--secondary)">search</span>
            </div>
            <div class="stat-value">1.2M</div>
            <div style="height: 4px; background: var(--surface-container); border-radius: 2px; margin-top: 16px;">
                <div style="width: 78%; height: 100%; background: var(--secondary-container); border-radius: 2px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                <span class="mono" style="font-size: 11px; opacity: 0.6;">Target: 1.5M</span>
                <span class="mono" style="font-size: 11px; color: var(--secondary); font-weight: 700;">+12.4%</span>
            </div>
        </div>
        <div class="card" style="grid-column: span 4;">
            <div style="display: flex; justify-content: space-between;">
                <span class="text-label-sm">Scraping Success Rate</span>
                <span class="material-symbols-outlined" style="color: var(--secondary)">data_exploration</span>
            </div>
            <div class="stat-value">99.8%</div>
            <div style="display: flex; gap: 4px; height: 32px; align-items: flex-end; margin-top: 16px;">
                <div style="flex: 1; height: 40%; background: var(--secondary); border-radius: 2px 2px 0 0;"></div>
                <div style="flex: 1; height: 70%; background: var(--secondary); border-radius: 2px 2px 0 0;"></div>
                <div style="flex: 1; height: 60%; background: var(--secondary); border-radius: 2px 2px 0 0;"></div>
                <div style="flex: 1; height: 100%; background: var(--secondary-container); border-radius: 2px 2px 0 0;"></div>
                <div style="flex: 1; height: 80%; background: var(--secondary-container); border-radius: 2px 2px 0 0;"></div>
            </div>
            <p class="mono" style="font-size: 10px; opacity: 0.6; margin-top: 8px;">Last 7 days efficiency</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Current Pipeline Stepper
    st.markdown("""
    <div class="card" style="margin-top: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--outline-variant); padding-bottom: 16px; margin-bottom: 24px;">
            <h3 class="text-h3" style="margin: 0;">Current Pipeline: SEO_Global_Enrichment_v2</h3>
            <div style="background: #d1fae5; color: #065f46; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                <span style="width: 8px; height: 8px; background: #10b981; border-radius: 50%;"></span> Running
            </div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 40px;">
            <div style="text-align: center;">
                <div style="width: 48px; height: 48px; background: var(--secondary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px;"><span class="material-symbols-outlined">input</span></div>
                <div class="mono" style="font-size: 12px;">Ingestion</div>
                <div class="mono" style="font-size: 9px; opacity: 0.5;">COMPLETE</div>
            </div>
            <div style="flex-grow: 1; height: 2px; background: var(--secondary); margin: 0 16px; margin-top: -30px;"></div>
            <div style="text-align: center;">
                <div style="width: 48px; height: 48px; background: var(--secondary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px; box-shadow: 0 0 0 4px var(--secondary-container);"><span class="material-symbols-outlined">database</span></div>
                <div class="mono" style="font-size: 12px;">Scraping</div>
                <div class="mono" style="font-size: 9px; color: var(--secondary); font-weight: 700;">ACTIVE</div>
            </div>
            <div style="flex-grow: 1; height: 2px; border-top: 2px dashed var(--outline-variant); margin: 0 16px; margin-top: -30px;"></div>
            <div style="text-align: center; opacity: 0.5;">
                <div style="width: 48px; height: 48px; border: 2px solid var(--outline-variant); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px;"><span class="material-symbols-outlined">psychology</span></div>
                <div class="mono" style="font-size: 12px;">IA Enrichment</div>
                <div class="mono" style="font-size: 9px;">PENDING</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bottom Row: Table + Insights
    st.markdown("""
    <div class="bento-grid" style="margin-top: 24px;">
        <div class="card" style="grid-column: span 8;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 class="text-h3" style="margin: 0;">Execution History</h3>
                <a href="#" style="color: var(--secondary); font-family: 'JetBrains Mono'; font-size: 13px; font-weight: 700; text-decoration: none;">View All →</a>
            </div>
            <table class="data-table">
                <thead>
                    <tr><th>Pipeline ID</th><th>Start Time</th><th>Volume</th><th>Status</th><th>Action</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="mono" style="font-weight: 700;">KS-RUN-8821</td>
                        <td>2023-10-24 <br><span style="font-size: 11px; opacity: 0.5;">14:32:01 UTC</span></td>
                        <td class="mono">245,000 req</td>
                        <td><span class="tag-success">SUCCESS</span></td>
                        <td><span class="material-symbols-outlined" style="opacity: 0.5;">visibility</span></td>
                    </tr>
                    <tr>
                        <td class="mono" style="font-weight: 700;">KS-RUN-8820</td>
                        <td>2023-10-24 <br><span style="font-size: 11px; opacity: 0.5;">11:15:44 UTC</span></td>
                        <td class="mono">12,400 req</td>
                        <td><span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">FAILED</span></td>
                        <td><span class="material-symbols-outlined" style="opacity: 0.5;">visibility</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div style="grid-column: span 4; display: flex; flex-direction: column; gap: 24px;">
            <div class="card insight-card">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <span class="material-symbols-outlined" style="color: var(--secondary);">tips_and_updates</span>
                    <h3 class="text-h3" style="margin: 0;">Key Insight</h3>
                </div>
                <p style="font-style: italic; font-size: 14px; color: var(--on-surface-variant);">"Current scraping latency in EU-West is 15% higher than US-East. Consider redistributing node weight for the next batch."</p>
                <button class="btn-outline" style="margin-top: 16px;">Apply Auto-Rebalance</button>
            </div>
            <div class="card dark-card">
                <h3 class="text-h3" style="color: white; margin: 0;">Ready for Export?</h3>
                <p style="font-size: 14px; opacity: 0.8; margin-top: 8px;">3 datasets are compiled and ready for CSV/JSON transmission.</p>
                <div style="display: flex; gap: 8px; margin-top: 20px;">
                    <button style="flex: 1; background: var(--secondary-container); color: var(--on-surface); border: none; padding: 8px; border-radius: 4px; font-weight: 700; cursor: pointer;">Download</button>
                    <button style="flex: 1; background: rgba(255,255,255,0.1); color: white; border: none; padding: 8px; border-radius: 4px; font-weight: 700; cursor: pointer;">API Sync</button>
                </div>
                <span class="material-symbols-outlined bolt-icon">bolt</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == "Data Input":
    st.markdown("<h2 class='text-h1'>Configuración de Búsqueda</h2>", unsafe_allow_html=True)
    st.markdown("<p class='text-body-sm'>Define los parámetros de entrada para la extracción y enriquecimiento de datos SEO.</p>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        # Keyword Input
        st.markdown("""
        <div class="card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--outline-variant); padding-bottom: 16px;">
                <span class="material-symbols-outlined" style="color: var(--secondary);">key</span>
                <h3 class="text-h3" style="margin: 0;">Palabras Clave (Keywords)</h3>
            </div>
            <div style="margin-bottom: 8px; font-weight: 700;">Ingresar Keywords</div>
            <p style="font-size: 13px; color: var(--on-surface-variant); margin-bottom: 16px;">Introduce una keyword por línea o separadas por comas para el análisis masivo.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Streamlit Text Area (Injected into the design)
        # To make it look "inside" the card, we use a negative margin trick or a simple container
        kw_input = st.text_area("Keywords", height=250, label_visibility="collapsed", placeholder="ej: mejores herramientas seo 2024...")
        
        st.markdown("""<div style="margin-top: -16px; padding: 0 24px 24px; background: white; border: 1px solid var(--outline-variant); border-top: none; border-radius: 0 0 12px 12px; display: flex; justify-content: space-between; align-items: center;">
            <span class="mono" style="font-size: 11px; opacity: 0.6;">0 / 500 keywords detectadas</span>
            <span class="mono" style="font-size: 11px; color: var(--secondary); cursor: pointer;">📄 Importar CSV</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div class="card">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--outline-variant); padding-bottom: 8px;">
                    <span class="material-symbols-outlined" style="color: var(--secondary);">public</span>
                    <h3 class="text-h3" style="margin: 0;">Segmentación</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.selectbox("País de Búsqueda", options=["España (es-ES)", "México (es-MX)", "Colombia (es-CO)"])
        with c2:
            st.markdown("""
            <div class="card">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--outline-variant); padding-bottom: 8px;">
                    <span class="material-symbols-outlined" style="color: var(--secondary);">settings_account_box</span>
                    <h3 class="text-h3" style="margin: 0;">Perfil de Búsqueda</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.radio("Agente", ["Desktop (Chrome/MacOS)", "Mobile (Safari/iOS)", "Deep Scan"], label_visibility="collapsed")

    with col_r:
        # Project Validation
        st.markdown("""
        <div class="card dark-card">
            <h3 class="text-h3" style="color: white; margin-bottom: 24px;">Validación del Proyecto</h3>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 12px;">
                <span style="opacity: 0.8; font-size: 14px;">Keywords configuradas</span>
                <span class="mono" style="color: var(--secondary-container); font-weight: 700;">Listo</span>
            </div>
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 12px;">
                <span style="opacity: 0.8; font-size: 14px;">Segmentación Geográfica</span>
                <span class="mono" style="color: var(--secondary-container); font-weight: 700;">Listo</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 24px;">
                <span style="opacity: 0.8; font-size: 14px;">Proxies Disponibles</span>
                <span class="mono" style="color: #ef4444; font-weight: 700;">Revisar</span>
            </div>
            <div style="margin-top: 32px; border-top: 1px solid rgba(255,255,255,0.2); pt-16px;">
                <div class="text-label-sm" style="opacity: 0.6;">Consumo Estimado</div>
                <div style="font-size: 32px; font-weight: 700;">450 <span style="font-size: 16px; opacity: 0.6; font-weight: 400;">Créditos</span></div>
            </div>
            <button style="width: 100%; background: var(--secondary-container); color: var(--on-surface); border: none; border-radius: 8px; padding: 16px; font-weight: 700; margin-top: 24px; cursor: pointer; font-size: 16px;">▶ INICIAR PIPELINE</button>
        </div>
        """, unsafe_allow_html=True)
        
        # IA Suggestion
        st.markdown("""
        <div class="card" style="padding: 0; overflow: hidden; margin-top: 24px;">
            <div style="height: 120px; background: #eee; overflow: hidden;">
                <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuDfjqnTyQkJL3MjkSg5AXVI71Nz68sZwRAvmng_uKhtT8LBUYvW3rzyM2UY46DMYpfkiOX6huxgXgrgFa-Bt9oCMvMekyg2dzBnL7cwhjrMw_WluKSsiqwMp8_CVwC49I7vU2ReeUYV4a623HVlgUic954OKEEoogMTVqdPJm6gJAsoX0VKi_SVPuofJ7XKSWXA9vSnhnr3gKVYs0Dc3PQKcb1CqXeMJTkY_ICCj9ulDDHQXVu9qvIYyQ-2ghpJEC68AuMnIywiwo5z" style="width: 100%; height: 100%; object-fit: cover;">
            </div>
            <div style="padding: 24px;">
                <h3 class="text-h3">Sugerencia de IA</h3>
                <p style="font-size: 13px; color: var(--on-surface-variant); margin-top: 8px;">Basado en tus keywords, te recomendamos activar el módulo de Análisis de Sentimiento.</p>
                <div style="color: var(--secondary); font-weight: 700; font-size: 13px; margin-top: 16px; cursor: pointer;">Activar módulo →</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True) # End stitch-main
