"""
Fixtures compartidas para todos los tests de KeySearch.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fixtures de Keywords ─────────────────────────────────────────────────────
@pytest.fixture
def keyword_simple():
    return "marketing digital"


@pytest.fixture
def keyword_larga():
    return "tarjetas de credito bancolombia"


@pytest.fixture
def keyword_especial():
    return "recetas de cocina mexicana"


@pytest.fixture
def sugerencias_base():
    return [
        "marketing digital",
        "marketing digital para empresas",
        "curso de marketing digital",
        "marketing digital precios",
        "que es marketing digital",
        "marketing digital en colombia",
        "estrategias de marketing digital",
        "marketing digital redes sociales",
    ]


@pytest.fixture
def preguntas_paa():
    return [
        "que es marketing digital",
        "como aprender marketing digital",
        "cuanto cuesta un curso de marketing digital",
        "cuales son las herramientas de marketing digital",
        "donde estudiar marketing digital en colombia",
    ]


@pytest.fixture
def preguntas_autocompletado():
    return [
        "marketing digital paso a paso",
        "marketing digital tips",
        "marketing digital para principiantes",
    ]


@pytest.fixture
def busquedas_relacionadas():
    return [
        "posicionamiento web",
        "community manager",
        "publicidad en linea",
        "email marketing",
    ]


@pytest.fixture
def search_context():
    return {
        "country_code": "co",
        "country_name": "Colombia",
        "language_code": "es",
        "google_ads_geo_targets": ["Colombia"],
    }


@pytest.fixture
def editorial_context():
    return {
        "category_name": "Marketing y Negocios",
        "subcategory_name": "Marketing Digital",
    }


# ── Fixtures de Metricas ─────────────────────────────────────────────────────
@pytest.fixture
def volumen_ejemplo():
    return {
        "marketing digital": {
            "score": 85.0,
            "categoria": "Muy alta",
            "fuente": "Autocompletado",
            "posicion_fuente": 1,
            "fuentes": ["Autocompletado"],
            "intencion": "Informativa",
            "funnel": "ToFU",
            "google_ads_avg_monthly_searches": 12000,
            "google_trends_promedio": 65.0,
            "wikipedia_visitas_mensuales": None,
        },
        "curso de marketing digital": {
            "score": 72.0,
            "categoria": "Alta",
            "fuente": "People Also Ask",
            "posicion_fuente": 2,
            "fuentes": ["People Also Ask"],
            "intencion": "Comercial",
            "funnel": "MoFU",
            "google_ads_avg_monthly_searches": 8500,
            "google_trends_promedio": 45.0,
            "wikipedia_visitas_mensuales": None,
        },
    }


@pytest.fixture
def keywords_para_filtrar():
    return [
        "marketing digital",
        "curso de marketing digital gratis online",
        "terremoto en colombia precio",
        "como aprender marketing digital",
        "marketing digital movistar",
        "marketing digital para empresas",
        "dibujos para pintar marketing",
        "estrategias de marketing digital 2026",
    ]


# ── Fixtures de Cache ────────────────────────────────────────────────────────
@pytest.fixture
def cache_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def cache_data():
    return {
        "url": "https://suggestqueries.google.com/complete/search?client=firefox&q=marketing",
        "text": json.dumps(["marketing digital", "marketing online"]),
        "status": 200,
    }


# ── Fixtures de HTML mock ────────────────────────────────────────────────────
@pytest.fixture
def mock_serp_html():
    return """
    <html>
    <body>
        <div id="center_col">
            <div class="g">
                <div>
                    <div data-sokoban-container>
                        <div>¿Qué es el marketing digital?</div>
                    </div>
                </div>
                <div>
                    <div data-sokoban-container>
                        <div>¿Cómo aprender marketing digital?</div>
                    </div>
                </div>
            </div>
            <div id="botstuff">
                <div>Relacionadas: posicionamiento web</div>
                <div>Relacionadas: community manager</div>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_serp_html_vacio():
    return "<html><body><div id='center_col'></div></body></html>"
