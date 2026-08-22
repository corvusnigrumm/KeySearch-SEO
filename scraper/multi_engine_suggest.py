"""
Módulo de sugerencias multi-motor (Multi-Engine Suggestion Engine).

Extrae sugerencias en tiempo real de forma 100% gratuita y sin límites de API:
1. Google Suggest (Búsqueda general y preguntas)
2. YouTube Suggest (Intención en video, tutoriales, comparativas, reviews)
3. Amazon Autosuggest (Intención comercial y transaccional, marcas, compras)
4. Bing Autosuggest (Motor Microsoft, variaciones regionales)
5. DuckDuckGo Autosuggest (Consultas neutrales y privadas)
"""

import json
import logging
import random
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import (
    CACHE_DIR,
    HTTP_CACHE_TTL_SECONDS,
    USER_AGENT_PROFILES,
)
from scraper.http_cache import get_text, make_key, set_text
from scraper.utils import es_relevante_riguroso, limpiar_texto

logger = logging.getLogger(__name__)


def _get_random_headers(lang: str = "es", country: str = "co") -> dict:
    perfil = random.choice(USER_AGENT_PROFILES)
    c_upper = country.upper()
    return {
        "User-Agent": perfil["ua"],
        "Accept": "*/*",
        "Accept-Language": f"{lang}-{c_upper},{lang};q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    }


def fetch_google_suggestions(
    query: str, lang: str = "es", country: str = "co", session: requests.Session = None
) -> list[str]:
    """Obtiene sugerencias de autocompletado de Google Search."""
    session = session or requests.Session()
    urls = [
        f"https://suggestqueries.google.com/complete/search?client=chrome&hl={lang}&gl={country}&q={urllib.parse.quote(query)}",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl={lang}&gl={country}&q={urllib.parse.quote(query)}",
    ]
    for url in urls:
        try:
            cache_key = make_key(url)
            cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
            if cached:
                data = json.loads(cached)
                if isinstance(data, list) and len(data) >= 2:
                    return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]

            headers = _get_random_headers(lang, country)
            resp = session.get(url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)
                if isinstance(data, list) and len(data) >= 2:
                    return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]
        except Exception:
            continue
    return []


def fetch_youtube_suggestions(
    query: str, lang: str = "es", country: str = "co", session: requests.Session = None
) -> list[str]:
    """Obtiene sugerencias de autocompletado de YouTube (Video & Tutorial Intent)."""
    session = session or requests.Session()
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl={lang}&gl={country}&q={urllib.parse.quote(query)}"
    try:
        cache_key = make_key(url)
        cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
        if cached:
            data = json.loads(cached)
            if isinstance(data, list) and len(data) >= 2:
                return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]

        headers = _get_random_headers(lang, country)
        headers["Referer"] = "https://www.youtube.com/"
        resp = session.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)
            if isinstance(data, list) and len(data) >= 2:
                return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]
    except Exception as e:
        logger.debug("YouTube Suggest error: %s", e)
    return []


def fetch_amazon_suggestions(
    query: str, lang: str = "es", country: str = "co", session: requests.Session = None
) -> list[str]:
    """Obtiene sugerencias de autocompletado de Amazon (Commercial & Purchase Intent)."""
    session = session or requests.Session()
    mid = "A1RKKUPIHCS9HS" if country.lower() in ("es", "espania") else "ATVPDKIKX0DER"
    url = f"https://completion.amazon.com/api/2017/suggestions?mid={mid}&alias=aps&prefix={urllib.parse.quote(query)}&suggestion-type=KEYWORD"
    try:
        cache_key = make_key(url)
        cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
        if cached:
            data = json.loads(cached)
            suggestions = [limpiar_texto(item["value"]) for item in data.get("suggestions", []) if "value" in item]
            if suggestions:
                return suggestions

        headers = _get_random_headers(lang, country)
        headers["Referer"] = "https://www.amazon.com/"
        resp = session.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)
            suggestions = [limpiar_texto(item["value"]) for item in data.get("suggestions", []) if "value" in item]
            return suggestions
    except Exception as e:
        logger.debug("Amazon Suggest error: %s", e)
    return []


def fetch_bing_suggestions(
    query: str, lang: str = "es", country: str = "co", session: requests.Session = None
) -> list[str]:
    """Obtiene sugerencias de autocompletado de Bing Search."""
    session = session or requests.Session()
    url = f"https://api.bing.com/osjson.aspx?query={urllib.parse.quote(query)}&language={lang}&market={country}"
    try:
        cache_key = make_key(url)
        cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
        if cached:
            data = json.loads(cached)
            if isinstance(data, list) and len(data) >= 2:
                return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]

        headers = _get_random_headers(lang, country)
        headers["Referer"] = "https://www.bing.com/"
        resp = session.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)
            if isinstance(data, list) and len(data) >= 2:
                return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]
    except Exception as e:
        logger.debug("Bing Suggest error: %s", e)
    return []


def fetch_duckduckgo_suggestions(
    query: str, lang: str = "es", country: str = "co", session: requests.Session = None
) -> list[str]:
    """Obtiene sugerencias de autocompletado de DuckDuckGo."""
    session = session or requests.Session()
    url = f"https://duckduckgo.com/ac/?q={urllib.parse.quote(query)}&type=list"
    try:
        cache_key = make_key(url)
        cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
        if cached:
            data = json.loads(cached)
            if isinstance(data, list) and len(data) >= 2:
                return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]

        headers = _get_random_headers(lang, country)
        resp = session.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)
            if isinstance(data, list) and len(data) >= 2:
                return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]
            elif isinstance(data, list):
                return [limpiar_texto(item["phrase"]) for item in data if isinstance(item, dict) and "phrase" in item]
    except Exception as e:
        logger.debug("DuckDuckGo Suggest error: %s", e)
    return []


def fetch_multi_engine_suggestions(
    keyword: str,
    lang: str = "es",
    country: str = "co",
    engines: list[str] = None,
) -> dict[str, dict]:
    """
    Ejecuta la extracción multi-motor para una keyword y retorna un diccionario:
    {
        "keyword_sugerida": {
            "engines": ["Google", "YouTube", "Amazon", "Bing"],
            "engine_count": 4,
            "intents": ["Informativo", "Comercial"],
            "primary_engine": "Google",
            "posicion": 1
        }
    }
    """
    if engines is None:
        engines = ["google", "youtube", "amazon", "bing", "duckduckgo"]

    session = requests.Session()
    results: dict[str, dict] = {}

    engine_fetchers = {
        "Google": (fetch_google_suggestions, "Informativo / General"),
        "YouTube": (fetch_youtube_suggestions, "Video / Tutorial"),
        "Amazon": (fetch_amazon_suggestions, "Comercial / Transaccional"),
        "Bing": (fetch_bing_suggestions, "Búsqueda Web"),
        "DuckDuckGo": (fetch_duckduckgo_suggestions, "Búsqueda Web"),
    }

    def _fetch_engine(engine_name, fetcher_func, intent_tag):
        try:
            sugs = fetcher_func(keyword, lang=lang, country=country, session=session)
            engine_results = {}
            for pos, sug in enumerate(sugs, start=1):
                if not es_relevante_riguroso(keyword, sug):
                    continue
                if sug not in engine_results:
                    engine_results[sug] = {
                        "engines": [engine_name],
                        "engine_count": 1,
                        "intents": [intent_tag],
                        "primary_engine": engine_name,
                        "best_pos": pos,
                    }
            return engine_results
        except Exception as err:
            logger.debug("Error procesando motor %s: %s", engine_name, err)
            return {}

    active_engines = [
        (name, func, intent)
        for name, (func, intent) in engine_fetchers.items()
        if name.lower() in [e.lower() for e in engines]
    ]

    with ThreadPoolExecutor(max_workers=min(5, len(active_engines))) as executor:
        futures = {
            executor.submit(_fetch_engine, name, func, intent): name
            for name, func, intent in active_engines
        }
        for future in as_completed(futures):
            try:
                engine_results = future.result()
                for sug, meta in engine_results.items():
                    if sug not in results:
                        results[sug] = meta
                    else:
                        for eng in meta["engines"]:
                            if eng not in results[sug]["engines"]:
                                results[sug]["engines"].append(eng)
                                results[sug]["engine_count"] += 1
                        for intent in meta["intents"]:
                            if intent not in results[sug]["intents"]:
                                results[sug]["intents"].append(intent)
                        if meta["best_pos"] < results[sug]["best_pos"]:
                            results[sug]["best_pos"] = meta["best_pos"]
            except Exception:
                pass

    return results
