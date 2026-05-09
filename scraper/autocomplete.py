"""
Módulo para obtener sugerencias de autocompletado de Google.

Usa el endpoint semi-público de Google Suggest que devuelve JSON
con las sugerencias que aparecen al escribir en la barra de búsqueda.

También genera preguntas frecuentes combinando la keyword con
prefijos de preguntas comunes en español.
"""
import time
import random
import requests
import logging
import json
from typing import List

from config import (
    AUTOCOMPLETE_URL,
    LANG,
    COUNTRY,
    USER_AGENTS,
    USER_AGENT_PROFILES,
    QUESTION_MODIFIERS,
    SEARCH_SUFFIXES,
    ALPHABET_EXPANSION,
    AUTOCOMPLETE_ALPHABET_LIMIT,
    DELAY_BETWEEN_REQUESTS,
    CACHE_DIR,
    HTTP_CACHE_TTL_SECONDS,
    AUTOCOMPLETE_DEEP_MIN_DELAY,
    AUTOCOMPLETE_DEEP_MAX_DELAY,
    AUTOCOMPLETE_PAA_RECURSIVE_DEPTH,
    AUTOCOMPLETE_DEEP_EXPANSION_LIMIT,
    SCRAPE_PROFILE,
)
from scraper.utils import dedupe_key, limpiar_texto
from scraper.http_cache import get_text, make_key, set_text

logger = logging.getLogger(__name__)


def _perfil_extremo(search_context: dict | None = None) -> bool:
    profile = (search_context or {}).get("scrape_profile", SCRAPE_PROFILE)
    return str(profile).strip().lower() in {"extreme", "ultra", "max"}


def _resolver_contexto(search_context: dict | None = None) -> dict:
    """Resuelve idioma y pais efectivos para la consulta."""
    return {
        "language_code": (search_context or {}).get("language_code", LANG),
        "country_code": (search_context or {}).get("country_code", COUNTRY),
    }


def _fetch_suggestions(
    query: str,
    search_context: dict | None = None,
    session: requests.Session | None = None,
) -> list:
    """
    Consulta el endpoint de autocompletado de Google y retorna la lista
    de sugerencias con headers anti-detección.
    """
    contexto = _resolver_contexto(search_context)
    lang = contexto["language_code"]
    country = contexto["country_code"].upper()

    url = AUTOCOMPLETE_URL.format(
        lang=lang,
        country=contexto["country_code"],
        query=requests.utils.quote(query),
    )

    # Usar un perfil completo para el autocompletado también
    perfil = random.choice(USER_AGENT_PROFILES)
    headers = {
        "User-Agent": perfil["ua"],
        "Accept": "*/*",
        "Accept-Language": f"{lang}-{country},{lang};q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
        "sec-ch-ua": perfil.get("sec-ch-ua", ""),
        "sec-ch-ua-mobile": perfil.get("sec-ch-ua-mobile", "?0"),
        "sec-ch-ua-platform": perfil.get("sec-ch-ua-platform", '"Windows"'),
    }
    # Limpiar keys vacias (ej. Firefox no tiene sec-ch-ua)
    headers = {k: v for k, v in headers.items() if v}

    try:
        session = session or requests.Session()
        cache_key = make_key(url)
        cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
        if cached:
            data = json.loads(cached)
            if isinstance(data, list) and len(data) >= 2:
                return [limpiar_texto(s) for s in data[1] if s]

        resp = session.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        set_text(CACHE_DIR, cache_key, resp.text, status=resp.status_code)
        data = resp.json()
        # El formato es: [query, [sugerencia1, sugerencia2, ...]]
        if isinstance(data, list) and len(data) >= 2:
            return [limpiar_texto(s) for s in data[1] if s]
        return []
    except Exception as exc:
        logger.debug("Autocomplete fallo para %s: %s", query, exc)
        return []



def get_autocomplete_suggestions(
    keyword: str,
    expandir: bool = True,
    search_context: dict | None = None,
) -> List[str]:
    """
    Obtiene sugerencias de autocompletado para una palabra clave.

    Args:
        keyword: Palabra clave a buscar.
        expandir: Si True, también busca con prefijos de preguntas
                  (qué, cómo, por qué, etc.) para obtener más resultados.

    Returns:
        Lista de sugerencias únicas (sin duplicados).
    """
    todas = []
    vistas = set()
    session = requests.Session()

    def _agregar(sugerencias: List[str]):
        for s in sugerencias:
            key = dedupe_key(s)
            if key and key not in vistas:
                vistas.add(key)
                todas.append(s)

    # Búsqueda base
    _agregar(_fetch_suggestions(keyword, search_context, session=session))

    if expandir:
        # Expandir con modificadores de preguntas
        for mod in QUESTION_MODIFIERS:
            _agregar(_fetch_suggestions(f"{mod}{keyword}", search_context, session=session))
            time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

        # Expandir con sufijos
        for suf in SEARCH_SUFFIXES:
            _agregar(_fetch_suggestions(f"{keyword}{suf}", search_context, session=session))
            time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

        for letra in ALPHABET_EXPANSION[:max(0, AUTOCOMPLETE_ALPHABET_LIMIT)]:
            _agregar(_fetch_suggestions(f"{keyword} {letra}", search_context, session=session))
            time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

    # En modo extremo: rondas recursivas sobre las mejores sugerencias encontradas
    if _perfil_extremo(search_context) and todas:
        factor = 2
        profundidad = max(1, int(AUTOCOMPLETE_PAA_RECURSIVE_DEPTH)) * factor
        limite = max(1, int(AUTOCOMPLETE_DEEP_EXPANSION_LIMIT)) * factor
        semillas = list(todas[:limite])
        for _ in range(profundidad):
            nuevas = []
            for semilla in semillas:
                sugerencias_extra = _fetch_suggestions(semilla, search_context, session=session)
                for s in sugerencias_extra:
                    key = dedupe_key(s)
                    if key and key not in vistas:
                        vistas.add(key)
                        todas.append(s)
                        nuevas.append(s)
                time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))
            if not nuevas:
                break
            semillas = nuevas[:limite]

    return todas


def get_question_suggestions(keyword: str, search_context: dict | None = None) -> List[str]:
    """
    Genera preguntas específicas combinando la keyword con prefijos
    de preguntas comunes. Filtra solo resultados que parecen preguntas.

    Args:
        keyword: Palabra clave a buscar.

    Returns:
        Lista de preguntas encontradas.
    """
    preguntas = []
    vistas = set()
    session = requests.Session()

    # Prefijos extendidos de preguntas
    prefijos_preguntas = [
        "qué es ",
        "qué significa ",
        "cómo funciona ",
        "cómo hacer ",
        "cómo se usa ",
        "por qué ",
        "cuándo ",
        "dónde ",
        "quién ",
        "cuál es ",
        "cuánto cuesta ",
        "cuánto vale ",
        "para qué sirve ",
        "es bueno ",
        "es malo ",
        "se puede ",
        "cómo saber ",
        "cómo elegir ",
        "diferencia entre ",
        "ventajas de ",
        "desventajas de ",
    ]

    if _perfil_extremo(search_context):
        prefijos_preguntas.extend([
            "ejemplos de ",
            "tipos de ",
            "cuales son los ",
            "historia de ",
            "origen de ",
            "caracteristicas de ",
            "beneficios de ",
            "riesgos de ",
            "alternativas a ",
            "precio de ",
            "costo de ",
            "donde comprar ",
            "donde conseguir ",
            "como arreglar ",
            "como solucionar ",
            "por que es importante ",
            "es necesario ",
            "es obligatorio ",
            "es seguro ",
            "es legal ",
            "opiniones sobre ",
            "reseñas de ",
            "tutorial de ",
            "guia de ",
            "pasos para ",
            "requisitos para ",
            "mejores ",
            "el mejor ",
            "la mejor ",
            "peores ",
            "mitos sobre ",
            "verdades sobre ",
            "secretos de ",
            "trucos para ",
            "tips para ",
        ])


    for prefijo in prefijos_preguntas:
        query = f"{prefijo}{keyword}"
        sugerencias = _fetch_suggestions(query, search_context, session=session)
        for s in sugerencias:
            key = dedupe_key(s)
            if key and key not in vistas:
                vistas.add(key)
                preguntas.append(s)
        time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))

    # Expansion recursiva para no dejar preguntas sin descubrir
    extra_factor = 2 if _perfil_extremo(search_context) else 1
    profundidad = max(1, int(AUTOCOMPLETE_PAA_RECURSIVE_DEPTH)) * extra_factor
    limite_semillas = max(1, int(AUTOCOMPLETE_DEEP_EXPANSION_LIMIT)) * extra_factor
    semillas = list(preguntas[:limite_semillas])
    for _ in range(profundidad):
        nuevas = []
        for semilla in semillas:
            sugerencias = _fetch_suggestions(semilla, search_context, session=session)
            for s in sugerencias:
                key = dedupe_key(s)
                if key and key not in vistas:
                    vistas.add(key)
                    preguntas.append(s)
                    nuevas.append(s)
            time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))
        if not nuevas:
            break
        semillas = nuevas[:limite_semillas]

    return preguntas
