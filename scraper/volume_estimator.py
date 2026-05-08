"""
Motor de metricas para keywords.

Este modulo ya no inventa rangos mensuales de busqueda. En su lugar:
1. Conserva senales reales observables de Google
2. Calcula un score de prioridad interno para ordenar temas
3. Adjunta datos de Google Trends cuando estan disponibles
"""
import random
import time
from typing import Dict, List

from config import COUNTRY, LANG

try:
    from pytrends.request import TrendReq

    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False


SOURCE_LABELS = {
    "autocomplete": "Autocompletado",
    "paa": "People Also Ask",
    "question_autocomplete": "Preguntas por autocompletado",
    "related": "Busquedas relacionadas",
}

SOURCE_WEIGHTS = {
    "autocomplete": 1.0,
    "paa": 0.75,
    "question_autocomplete": 0.6,
    "related": 0.65,
}

TRENDS_TIMEFRAME = "today 12-m"
TRENDS_BATCH_SIZE = 5


def _score_por_posicion(posicion: int, total: int, peso_fuente: float) -> float:
    """
    Calcula un score de prioridad interno a partir de la posicion.

    Este score sirve para ordenar temas dentro del reporte. No representa
    volumen mensual exacto ni debe leerse como una cifra oficial de Google.
    """
    if total <= 0:
        return 0.0

    ratio = 1 - (posicion / max(total, 1))
    score = (ratio**0.7) * 100 * peso_fuente
    return round(min(100, max(0, score)), 1)


def _categorizar_prioridad(score: float) -> str:
    """Convierte un score interno en una banda de prioridad editorial."""
    if score >= 80:
        return "Muy alta"
    if score >= 55:
        return "Alta"
    if score >= 30:
        return "Media"
    if score >= 15:
        return "Baja"
    return "Muy baja"


def _registrar_items(
    metricas: Dict[str, dict],
    items: List[str],
    source_key: str,
    metadata: dict | None = None,
) -> None:
    """Registra items con su procedencia y posicion dentro de la fuente."""
    total = len(items)
    peso = SOURCE_WEIGHTS[source_key]
    fuente = SOURCE_LABELS[source_key]
    metadata = metadata or {}

    for posicion, texto in enumerate(items):
        score = _score_por_posicion(posicion, total, peso)
        prioridad = _categorizar_prioridad(score)
        source_rank = posicion + 1

        if texto not in metricas:
            metricas[texto] = {
                "score": score,
                "categoria": prioridad,
                "categoria_padre": metadata.get("categoria_padre", ""),
                "subcategoria": metadata.get("subcategoria", ""),
                "referencia": metadata.get("referencia", ""),
                "pais": metadata.get("pais", ""),
                "pais_codigo": metadata.get("pais_codigo", ""),
                "google_ads_geo_targets": list(metadata.get("google_ads_geo_targets", [])),
                "fuente": fuente,
                "posicion_fuente": source_rank,
                "fuentes": [fuente],
                "trends": None,
                "google_trends_promedio": None,
                "google_trends_pico": None,
                "google_trends_ultimo": None,
                "google_trends_timeframe": None,
                "google_trends_geo": None,
                "google_ads_keyword_text": None,
                "google_ads_close_variants": [],
                "google_ads_avg_monthly_searches": None,
                "google_ads_competition": None,
                "google_ads_competition_index": None,
                "google_ads_low_top_of_page_bid_micros": None,
                "google_ads_high_top_of_page_bid_micros": None,
                "google_ads_monthly_search_volumes": [],
            }
            continue

        existente = metricas[texto]
        if fuente not in existente["fuentes"]:
            existente["fuentes"].append(fuente)

        if score > existente["score"]:
            existente["score"] = score
            existente["categoria"] = prioridad
            existente["fuente"] = fuente
            existente["posicion_fuente"] = source_rank


def _obtener_trends_batch(keywords: List[str]) -> Dict[str, dict]:
    """
    Consulta Google Trends para un grupo de keywords.

    Devuelve metadatos reales de interes relativo (0-100) durante los
    ultimos 12 meses para el pais configurado.
    """
    if not HAS_PYTRENDS:
        return {}

    try:
        pytrends = TrendReq(hl=LANG, tz=360, timeout=(10, 25))
        batch = keywords[:TRENDS_BATCH_SIZE]

        pytrends.build_payload(
            batch,
            cat=0,
            timeframe=TRENDS_TIMEFRAME,
            geo=COUNTRY.upper(),
            gprop="",
        )

        df = pytrends.interest_over_time()
        if df.empty:
            return {}

        resultados = {}
        for keyword in batch:
            if keyword not in df.columns:
                continue

            serie = df[keyword]
            resultados[keyword] = {
                "promedio": round(float(serie.mean()), 1),
                "pico": int(serie.max()),
                "ultimo": int(serie.iloc[-1]),
                "timeframe": TRENDS_TIMEFRAME,
                "geo": COUNTRY.upper(),
            }

        return resultados
    except Exception:
        return {}


def _obtener_trends_batch_contextual(
    keywords: List[str],
    search_context: dict | None = None,
) -> Dict[str, dict]:
    """Consulta Trends respetando el pais seleccionado en la corrida."""
    if not HAS_PYTRENDS:
        return {}

    contexto = search_context or {}
    language_code = contexto.get("language_code", LANG)
    country_code = contexto.get("country_code", COUNTRY).upper()

    try:
        pytrends = TrendReq(hl=language_code, tz=360, timeout=(10, 25))
        batch = keywords[:TRENDS_BATCH_SIZE]

        pytrends.build_payload(
            batch,
            cat=0,
            timeframe=TRENDS_TIMEFRAME,
            geo=country_code,
            gprop="",
        )

        df = pytrends.interest_over_time()
        if df.empty:
            return {}

        resultados = {}
        for keyword in batch:
            if keyword not in df.columns:
                continue

            serie = df[keyword]
            resultados[keyword] = {
                "promedio": round(float(serie.mean()), 1),
                "pico": int(serie.max()),
                "ultimo": int(serie.iloc[-1]),
                "timeframe": TRENDS_TIMEFRAME,
                "geo": country_code,
            }

        return resultados
    except Exception:
        return {}


def estimar_volumenes(
    keyword_principal: str,
    sugerencias: List[str],
    preguntas_paa: List[str],
    preguntas_autocompletado: List[str],
    busquedas_relacionadas: List[str],
    usar_trends: bool = True,
    progress_callback=None,
    metadata: dict | None = None,
    search_context: dict | None = None,
) -> Dict[str, dict]:
    """
    Analiza keywords usando solo senales reales y score interno de prioridad.

    Se conserva el nombre de la funcion para no romper el resto del proyecto,
    pero el resultado ya no intenta fingir volumenes mensuales.
    """
    del keyword_principal

    metricas: Dict[str, dict] = {}

    if progress_callback:
        progress_callback("Registrando senales reales por fuente y posicion...")

    _registrar_items(metricas, sugerencias, "autocomplete", metadata)
    _registrar_items(metricas, preguntas_paa, "paa", metadata)
    _registrar_items(metricas, preguntas_autocompletado, "question_autocomplete", metadata)
    _registrar_items(metricas, busquedas_relacionadas, "related", metadata)

    if usar_trends and HAS_PYTRENDS and metricas:
        if progress_callback:
            progress_callback("Consultando Google Trends para las keywords con mayor prioridad...")

        top_keywords = sorted(
            metricas.keys(),
            key=lambda keyword: metricas[keyword]["score"],
            reverse=True,
        )[:25]

        trends_data: Dict[str, dict] = {}
        total_batches = (len(top_keywords) + TRENDS_BATCH_SIZE - 1) // TRENDS_BATCH_SIZE

        for batch_index in range(0, len(top_keywords), TRENDS_BATCH_SIZE):
            batch = top_keywords[batch_index:batch_index + TRENDS_BATCH_SIZE]

            if progress_callback:
                progress_callback(
                    f"Google Trends: lote {batch_index // TRENDS_BATCH_SIZE + 1}/{max(total_batches, 1)}..."
                )

            trends_data.update(_obtener_trends_batch_contextual(batch, search_context))
            time.sleep(random.uniform(1.0, 2.0))

        if trends_data:
            max_promedio = max(data["promedio"] for data in trends_data.values()) or 1

            for keyword, trend_data in trends_data.items():
                if keyword not in metricas:
                    continue

                trend_normalized = (trend_data["promedio"] / max_promedio) * 100
                combined_score = (trend_normalized * 0.6) + (metricas[keyword]["score"] * 0.4)

                metricas[keyword]["score"] = round(combined_score, 1)
                metricas[keyword]["categoria"] = _categorizar_prioridad(combined_score)
                metricas[keyword]["trends"] = trend_data["promedio"]
                metricas[keyword]["google_trends_promedio"] = trend_data["promedio"]
                metricas[keyword]["google_trends_pico"] = trend_data["pico"]
                metricas[keyword]["google_trends_ultimo"] = trend_data["ultimo"]
                metricas[keyword]["google_trends_timeframe"] = trend_data["timeframe"]
                metricas[keyword]["google_trends_geo"] = trend_data["geo"]

            if progress_callback:
                progress_callback(f"OK Google Trends: {len(trends_data)} keywords enriquecidas")
        elif progress_callback:
            progress_callback("Google Trends no devolvio datos para esta consulta")
    elif progress_callback:
        if not HAS_PYTRENDS:
            progress_callback("pytrends no esta instalado: se exportaran solo senales observables")
        else:
            progress_callback("Google Trends desactivado: se exportaran solo senales observables")

    return metricas


def ordenar_por_volumen(items: List[str], volumenes: Dict[str, dict]) -> List[str]:
    """Ordena priorizando Google Ads si existe; si no, usa el score interno."""
    return sorted(
        items,
        key=lambda item: (
            volumenes.get(item, {}).get("google_ads_avg_monthly_searches") is not None,
            volumenes.get(item, {}).get("google_ads_avg_monthly_searches") or 0,
            volumenes.get(item, {}).get("score", 0),
        ),
        reverse=True,
    )
