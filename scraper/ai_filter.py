"""
Filtrado de keywords: pre-filtro determinista + filtro IA por lotes.
"""
import json
import logging
import re

from config import GROQ_API_KEY
from scraper.ai_client import post_groq_json

logger = logging.getLogger(__name__)

_MARCAS_COMERCIALES = [
    "claro", "movistar", "tigo", "etb", "une", "wom", "virgin", "directv",
    "netflix", "spotify", "amazon", "apple", "samsung", "huawei", "xiaomi",
    "mercadolibre", "rappi", "uber", "ifood", "didi", "cabify",
    "bancolombia", "davivienda", "bbva", "nequi", "daviplata", "bancamia",
]

_PATRONES_SEO_INUTILES = [
    r"\bpara colorear\b",
    r"\bdibujos?\b.*\bperro\b",
    r"\bjuego(s)?\b",
    r"\bvideo(s)?\b",
    r"\bcancion(es)?\b",
    r"\bcuento(s)?\b",
    r"\bpintar\b",
    r"\bcartoon\b",
    r"\bpelicula(s)?\b",
    r"\bserie(s)?\b",
]

_BATCH_SIZE = 40

_TEMAS_NO_TRANSACCIONALES = {
    "terremoto", "sismo", "temblor", "tsunami", "volcan", "erupcion", "inundacion",
    "huracan", "tornado", "desastre", "tragedia", "muerte", "fallecimiento", "funeral",
    "accidente", "asesinato", "cancer", "infarto", "enfermedad", "sintomas", "guerra",
    "masacre", "atentado", "emergencia", "historia", "biografia", "definicion", "significado",
    "clima", "temperatura", "hora", "fecha"
}

_MODIFICADORES_COMERCIALES_ABSURDOS = [
    r"\bgratis\b", r"\bgratuito\b", r"\bbarato\b", r"\bbarata\b", r"\bprecio\b",
    r"\bprecios\b", r"\bcosto\b", r"\bcostos\b", r"\bcomprar\b", r"\bventa\b",
    r"\bvender\b", r"\bdescuento\b", r"\bcupon\b", r"\btienda\b", r"\balquiler\b",
    r"\bdomicilio\b", r"\bdescargar\b", r"\bpdf gratis\b", r"\bcuanto vale\b",
]


def _es_tema_no_transaccional(keyword_base: str) -> bool:
    kb_lower = keyword_base.lower()
    palabras = set(re.findall(r"\w+", kb_lower))
    return bool(palabras.intersection(_TEMAS_NO_TRANSACCIONALES))


def _filtro_determinista(keywords: list[str], keyword_base: str) -> list[str]:
    """Pre-filtro rapido sin IA: elimina marcas, patrones inutiles e incongruencias."""
    kb_lower = keyword_base.lower()
    es_no_comercial = _es_tema_no_transaccional(keyword_base)
    resultado = []

    for kw in keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower or len(kw_lower) < 3:
            continue

        marca_encontrada = any(m in kw_lower and m not in kb_lower for m in _MARCAS_COMERCIALES)
        if marca_encontrada:
            continue

        if any(re.search(p, kw_lower) for p in _PATRONES_SEO_INUTILES):
            continue

        if es_no_comercial and any(re.search(m, kw_lower) for m in _MODIFICADORES_COMERCIALES_ABSURDOS):
            continue

        if re.search(r"\b(gratis online|online gratis|pdf descargar gratis)\b", kw_lower) and es_no_comercial:
            continue

        resultado.append(kw)
    return resultado


def _filtrar_lote_con_ia(lote: list[str], keyword_base: str, pais: str) -> list[str]:
    """Filtra un lote de keywords con una sola llamada a IA."""
    prompt = (
        f"Eres un analista SEO SENIOR para un medio digital en {pais}. "
        f"Filtra esta lista para el tema: '{keyword_base}'.\n\n"
        "ELIMINA: frases absurdas, menciones a otros paises, contenido infantil, marcas no solicitadas.\n"
        "CONSERVA: preguntas reales, variaciones informativas, dudas genuinas.\n\n"
        "Responde SOLO con un JSON Array de strings validos.\n\n"
        f"{json.dumps(lote, ensure_ascii=False)}"
    )

    try:
        filtered = post_groq_json(prompt, timeout=35)
        if isinstance(filtered, list):
            original_set = set(lote)
            return [kw for kw in filtered if kw in original_set]
        return lote
    except Exception as e:
        logger.warning("Error en filtro IA de lote: %s", e)
        return lote


def filtrar_con_ia(keywords: list[str], keyword_base: str, pais: str) -> list[str]:
    """
    Pipeline completo: pre-filtro determinista + filtro IA por lotes.
    """
    if not keywords:
        return keywords

    pre_filtradas = _filtro_determinista(keywords, keyword_base)
    logger.info(
        "Pre-filtro determinista: %d -> %d keywords",
        len(keywords), len(pre_filtradas),
    )

    if not GROQ_API_KEY or not pre_filtradas:
        return pre_filtradas

    resultado_final = []
    for i in range(0, len(pre_filtradas), _BATCH_SIZE):
        lote = pre_filtradas[i: i + _BATCH_SIZE]
        lote_filtrado = _filtrar_lote_con_ia(lote, keyword_base, pais)
        resultado_final.extend(lote_filtrado)

    return resultado_final
