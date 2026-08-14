"""
Motor de métricas y estimación de oportunidad para keywords.

Proporciona señales reales, transparentes y 100% gratuitas:
1. Puntuación compuesta de Oportunidad SEO (0-100)
2. Enriquecimiento cuantitativo real con Wikipedia Pageviews API
3. Métricas de Google Trends (Interés relativo 0-100 y consultas en aumento / Breakouts)
4. Clasificación de Intención de Búsqueda (Informativa, Comercial, Transaccional, Navegacional)
5. Etapa del Embudo de Conversión (ToFU, MoFU, BoFU)
"""
import random
import re
import time
from typing import Dict, List, Optional

from config import COUNTRY, LANG

try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False

from scraper.wikipedia_metrics import enriquecer_con_wikipedia


SOURCE_LABELS = {
    "autocomplete": "Autocompletado",
    "paa": "People Also Ask",
    "question_autocomplete": "Preguntas por autocompletado",
    "related": "Busquedas relacionadas",
    "youtube": "YouTube Video Search",
    "amazon": "Amazon E-Commerce",
    "bing": "Bing Autosuggest",
    "duckduckgo": "DuckDuckGo Autosuggest",
}

SOURCE_WEIGHTS = {
    "autocomplete": 1.0,
    "paa": 0.80,
    "question_autocomplete": 0.70,
    "related": 0.65,
    "youtube": 0.85,
    "amazon": 0.90,
    "bing": 0.70,
    "duckduckgo": 0.65,
}

TRENDS_TIMEFRAME = "today 12-m"
TRENDS_BATCH_SIZE = 5


# ─── Heurística de Intención y Funnel ─────────────────────────────────────────

_PATRONES_TRANSACCIONAL = [
    r"\bcomprar\b", r"\bprecio\b", r"\bprecios\b", r"\bcosto\b", r"\bcuanto cuesta\b",
    r"\bcuanto vale\b", r"\bbarato\b", r"\bdescuento\b", r"\boferta\b", r"\bpromocion\b",
    r"\btienda\b", r"\bventa\b", r"\bdonde comprar\b", r"\bplanes\b", r"\bpedir\b",
    r"\bcotizar\b", r"\bcotizacion\b", r"\btarifa\b", r"\bsuscripcion\b", r"\bordenar\b",
]

_PATRONES_COMERCIAL = [
    r"\bmejor(es)?\b", r"\btop\b", r"\bcomparativa\b", r"\bvs\b", r"\breseña(s)?\b",
    r"\breview(s)?\b", r"\bopiniones\b", r"\bventajas\b", r"\bdesventajas\b",
    r"\bbeneficios\b", r"\bmarcas\b", r"\brecomendados\b", r"\bcual elegir\b",
]

_PATRONES_INFORMATIVO = [
    r"\bque es\b", r"\bcomo\b", r"\bpor que\b", r"\bcuando\b", r"\bdonde\b",
    r"\bquien\b", r"\bpara que sirve\b", r"\bsignificado\b", r"\btutorial\b",
    r"\bguia\b", r"\bpasp a paso\b", r"\bdefinicion\b", r"\bejemplos\b",
    r"\btipos de\b", r"\bhistoria\b", r"\bcaracteristicas\b",
]


def detectar_intencion_y_funnel(keyword: str) -> tuple[str, str]:
    """
    Determina la intención de búsqueda y la etapa del embudo de conversión.
    Devuelve: (Intencion, Funnel)
    """
    kw_lower = keyword.lower()

    for p in _PATRONES_TRANSACCIONAL:
        if re.search(p, kw_lower):
            return "Transaccional", "BoFU (Decisión / Compra)"

    for p in _PATRONES_COMERCIAL:
        if re.search(p, kw_lower):
            return "Comercial / Investigación", "MoFU (Evaluación / Comparación)"

    for p in _PATRONES_INFORMATIVO:
        if re.search(p, kw_lower):
            return "Informativa", "ToFU (Descubrimiento / Aprendizaje)"

    # Por defecto
    palabras = kw_lower.split()
    if len(palabras) >= 4:
        return "Informativa (Long-Tail)", "ToFU (Descubrimiento / Aprendizaje)"

    return "Informativa / General", "ToFU (Descubrimiento / Aprendizaje)"


def _score_por_posicion(posicion: int, total: int, peso_fuente: float) -> float:
    """Calcula el score base de prioridad interno a partir de la posición."""
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
    """Registra items con su procedencia, intención y posición dentro de la fuente."""
    total = len(items)
    peso = SOURCE_WEIGHTS.get(source_key, 0.65)
    fuente = SOURCE_LABELS.get(source_key, source_key.title())
    metadata = metadata or {}

    for posicion, texto in enumerate(items):
        score = _score_por_posicion(posicion, total, peso)
        prioridad = _categorizar_prioridad(score)
        source_rank = posicion + 1
        intencion, funnel = detectar_intencion_y_funnel(texto)

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
                "intencion": intencion,
                "funnel": funnel,
                "engines_count": 1,
                "trends": None,
                "google_trends_promedio": None,
                "google_trends_pico": None,
                "google_trends_ultimo": None,
                "google_trends_rising": None,
                "google_trends_timeframe": None,
                "google_trends_geo": None,
                "wikipedia_visitas_mensuales": None,
                "wikipedia_promedio_diario": None,
                "wikipedia_articulo": None,
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
            existente["engines_count"] = len(existente["fuentes"])

        if score > existente["score"]:
            existente["score"] = score
            existente["categoria"] = prioridad
            existente["fuente"] = fuente
            existente["posicion_fuente"] = source_rank


def _obtener_trends_batch_contextual(
    keywords: List[str],
    search_context: dict | None = None,
) -> Dict[str, dict]:
    """Consulta Google Trends e identifica promedios y consultas en aumento (rising / breakout)."""
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
        resultados = {}

        if not df.empty:
            for keyword in batch:
                if keyword not in df.columns:
                    continue

                serie = df[keyword]
                resultados[keyword] = {
                    "promedio": round(float(serie.mean()), 1),
                    "pico": int(serie.max()),
                    "ultimo": int(serie.iloc[-1]),
                    "rising": False,
                    "timeframe": TRENDS_TIMEFRAME,
                    "geo": country_code,
                }

        # Intentar obtener consultas en aumento (rising queries)
        try:
            related_dict = pytrends.related_queries()
            for kw, data in related_dict.items():
                if kw in resultados and data and "rising" in data and data["rising"] is not None:
                    rising_df = data["rising"]
                    if not rising_df.empty:
                        resultados[kw]["rising"] = True
        except Exception:
            pass

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
    Analiza y cuantifica keywords combinando señales reales multi-motor,
    Google Trends y visitas cuantitativas reales de Wikipedia.
    """
    metricas: Dict[str, dict] = {}
    contexto = search_context or {}
    lang = contexto.get("language_code", LANG)

    if progress_callback:
        progress_callback("Registrando señales de búsqueda multi-motor...")

    _registrar_items(metricas, sugerencias, "autocomplete", metadata)
    _registrar_items(metricas, preguntas_paa, "paa", metadata)
    _registrar_items(metricas, preguntas_autocompletado, "question_autocomplete", metadata)
    _registrar_items(metricas, busquedas_relacionadas, "related", metadata)

    # 1. Enriquecimiento con métricas cuantitativas de Wikipedia
    if metricas:
        if progress_callback:
            progress_callback("Consultando métricas de demanda con Wikipedia Pageviews API...")
        try:
            top_kws = list(metricas.keys())[:15]
            # También incluir la keyword principal
            if keyword_principal and keyword_principal not in top_kws:
                top_kws.insert(0, keyword_principal)

            wiki_data = enriquecer_con_wikipedia(top_kws, lang=lang, max_items=12)
            for kw, w_info in wiki_data.items():
                if kw in metricas:
                    metricas[kw]["wikipedia_visitas_mensuales"] = w_info["visitas_mensuales"]
                    metricas[kw]["wikipedia_promedio_diario"] = w_info["promedio_diario"]
                    metricas[kw]["wikipedia_articulo"] = w_info["articulo"]
                    # Bonus al score por demanda cuantificada real
                    metricas[kw]["score"] = round(min(100, metricas[kw]["score"] + 10), 1)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Nota: Wikipedia API omitida ({e})")

    # 2. Enriquecimiento con Google Trends (Interés relativo y Rising queries)
    if usar_trends and HAS_PYTRENDS and metricas:
        if progress_callback:
            progress_callback("Consultando Google Trends y consultas en aumento...")

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
            time.sleep(random.uniform(1.0, 1.8))

        if trends_data:
            max_promedio = max(data["promedio"] for data in trends_data.values()) or 1

            for keyword, trend_data in trends_data.items():
                if keyword not in metricas:
                    continue

                trend_normalized = (trend_data["promedio"] / max_promedio) * 100
                # Bonus si es consulta en aumento (Rising/Breakout)
                rising_bonus = 15 if trend_data.get("rising") else 0

                # Presencia multi-fuente añade hasta +15 puntos
                multi_engine_bonus = min(15, (metricas[keyword].get("engines_count", 1) - 1) * 5)

                combined_score = (
                    (trend_normalized * 0.5)
                    + (metricas[keyword]["score"] * 0.35)
                    + rising_bonus
                    + multi_engine_bonus
                )

                metricas[keyword]["score"] = round(min(100, max(0, combined_score)), 1)
                metricas[keyword]["categoria"] = _categorizar_prioridad(metricas[keyword]["score"])
                metricas[keyword]["trends"] = trend_data["promedio"]
                metricas[keyword]["google_trends_promedio"] = trend_data["promedio"]
                metricas[keyword]["google_trends_pico"] = trend_data["pico"]
                metricas[keyword]["google_trends_ultimo"] = trend_data["ultimo"]
                metricas[keyword]["google_trends_rising"] = trend_data.get("rising", False)
                metricas[keyword]["google_trends_timeframe"] = trend_data["timeframe"]
                metricas[keyword]["google_trends_geo"] = trend_data["geo"]

            if progress_callback:
                progress_callback(f"OK Google Trends: {len(trends_data)} keywords enriquecidas")
        elif progress_callback:
            progress_callback("Google Trends finalizado")

    return metricas


def ordenar_por_volumen(items: List[str], volumenes: Dict[str, dict]) -> List[str]:
    """Ordena priorizando Google Ads si existe; si no, usa el score compuesto de oportunidad."""
    return sorted(
        items,
        key=lambda item: (
            volumenes.get(item, {}).get("google_ads_avg_monthly_searches") is not None,
            volumenes.get(item, {}).get("google_ads_avg_monthly_searches") or 0,
            volumenes.get(item, {}).get("wikipedia_visitas_mensuales") or 0,
            volumenes.get(item, {}).get("score", 0),
        ),
        reverse=True,
    )
