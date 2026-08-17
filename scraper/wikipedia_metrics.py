"""
Módulo para obtener métricas cuantitativas reales con Wikipedia Pageviews API.

La API de Wikimedia es 100% gratuita, oficial y no requiere claves.
Permite obtener el número exacto de visitas mensuales y diarias para entidades,
marcas, conceptos y temas clave, proporcionando un indicador cuantitativo real
de volumen y demanda de búsqueda.
"""

import datetime
import json
import logging
import random
import urllib.parse

import requests

from config import (
    CACHE_DIR,
    HTTP_CACHE_TTL_SECONDS,
    USER_AGENT_PROFILES,
)
from scraper.http_cache import get_text, make_key, set_text

logger = logging.getLogger(__name__)


def _get_headers() -> dict:
    perfil = random.choice(USER_AGENT_PROFILES)
    return {
        "User-Agent": f"KeySearch-SEO-Tool/6.0 (https://github.com/corvusnigrumm/KeySearch-SEO; info@keysearch.local) {perfil['ua']}",
        "Accept": "application/json",
    }


def _buscar_articulo_wikipedia(query: str, lang: str = "es", session: requests.Session = None) -> str | None:
    """Busca el título exacto del artículo en Wikipedia en el idioma objetivo."""
    session = session or requests.Session()
    api_url = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=1&namespace=0&format=json"
    try:
        cache_key = make_key(api_url)
        cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
        if cached:
            data = json.loads(cached)
            if isinstance(data, list) and len(data) >= 2 and data[1]:
                return data[1][0]

        headers = _get_headers()
        resp = session.get(api_url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)
            if isinstance(data, list) and len(data) >= 2 and data[1]:
                return data[1][0]
    except Exception as e:
        logger.debug("Wikipedia Search error: %s", e)
    return None


def obtener_vistas_wikipedia(
    query: str,
    lang: str = "es",
    meses_atras: int = 1,
    session: requests.Session = None,
) -> dict | None:
    """
    Obtiene las visitas mensuales del artículo de Wikipedia para el término o entidad.
    Retorna un dict con:
    {
        "articulo": "...",
        "visitas_mensuales": 12500,
        "promedio_diario": 416,
        "periodo": "2026-07"
    }
    """
    session = session or requests.Session()
    articulo = _buscar_articulo_wikipedia(query, lang=lang, session=session)
    if not articulo:
        return None

    articulo_url_encoded = urllib.parse.quote(articulo.replace(" ", "_"), safe="")

    # Calcular fechas del último mes completo
    now = datetime.datetime.now()
    # Tomamos el mes anterior para tener datos cerrados completos
    first_day_current_month = now.replace(day=1)
    last_day_prev_month = first_day_current_month - datetime.timedelta(days=1)
    start_date = last_day_prev_month.strftime("%Y%m01")
    end_date = last_day_prev_month.strftime("%Y%m%d")
    periodo_str = last_day_prev_month.strftime("%Y-%m")

    endpoint = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{lang}.wikipedia/all-access/all-agents/{articulo_url_encoded}/monthly/{start_date}/{end_date}"
    )

    try:
        cache_key = make_key(endpoint)
        cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
        if cached:
            data = json.loads(cached)
            items = data.get("items", [])
            if items:
                vistas = items[0].get("views", 0)
                dias = last_day_prev_month.day
                return {
                    "articulo": articulo,
                    "visitas_mensuales": vistas,
                    "promedio_diario": round(vistas / max(1, dias)),
                    "periodo": periodo_str,
                }

        headers = _get_headers()
        resp = session.get(endpoint, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)
            items = data.get("items", [])
            if items:
                vistas = items[0].get("views", 0)
                dias = last_day_prev_month.day
                return {
                    "articulo": articulo,
                    "visitas_mensuales": vistas,
                    "promedio_diario": round(vistas / max(1, dias)),
                    "periodo": periodo_str,
                }
    except Exception as e:
        logger.debug("Wikipedia Pageviews API error: %s", e)

    return None


def enriquecer_con_wikipedia(keywords: list[str], lang: str = "es", max_items: int = 15) -> dict[str, dict]:
    """
    Enriquece un lote de keywords principales con métricas de visitas reales de Wikipedia.
    """
    session = requests.Session()
    resultados: dict[str, dict] = {}

    for kw in keywords[:max_items]:
        datos = obtener_vistas_wikipedia(kw, lang=lang, session=session)
        if datos:
            resultados[kw] = datos

    return resultados
