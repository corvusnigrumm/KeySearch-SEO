"""
Módulo para extraer datos de la página de resultados de Google (SERP).

Usa peticiones HTTP puras con requests + BeautifulSoup — SIN navegador.
Combina múltiples estrategias:
  1. Parsing directo del HTML de la SERP
  2. Google Autocomplete con patrones de preguntas
  3. Búsquedas relacionadas via SERP y autocomplete

Extrae:
  - Preguntas frecuentes ("Más preguntas" / People Also Ask)
  - Búsquedas relacionadas
"""
import time
import random
import json
import logging
import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from config import (
    GOOGLE_SEARCH_URL,
    AUTOCOMPLETE_URL,
    LANG,
    COUNTRY,
    USER_AGENTS,
    HTTP_TIMEOUT,
    HTTP_MAX_RETRIES,
    HTTP_RETRY_DELAY,
    DELAY_BETWEEN_REQUESTS,
    SERP_NUM_RESULTS,
    SERP_PAGES,
    SERP_DEEP_MODE,
    SERP_QUERY_VARIANT_LIMIT,
    SERP_TBM_MODES,
    QUESTION_MODIFIERS,
    SEARCH_SUFFIXES,
    CACHE_DIR,
    HTTP_CACHE_TTL_SECONDS,
)
from scraper.utils import dedupe_key, limpiar_texto
from scraper.http_cache import get_text, make_key, set_text

logger = logging.getLogger(__name__)


def _resolver_contexto(search_context: dict | None = None) -> dict:
    """Resuelve idioma y pais efectivos para la consulta."""
    return {
        "language_code": (search_context or {}).get("language_code", LANG),
        "country_code": (search_context or {}).get("country_code", COUNTRY),
    }


def _get_random_headers(search_context: dict | None = None) -> dict:
    """Genera headers HTTP aleatorios que imitan un navegador real."""
    ua = random.choice(USER_AGENTS)
    contexto = _resolver_contexto(search_context)
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": (
            f"{contexto['language_code']}-{contexto['country_code'].upper()},"
            f"{contexto['language_code']};q=0.9,en-US;q=0.7,en;q=0.5"
        ),
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def _hacer_request(
    url: str,
    progress_callback=None,
    search_context: dict | None = None,
    session: requests.Session | None = None,
) -> Optional[str]:
    """
    Realiza una petición HTTP GET con reintentos y backoff.

    Returns:
        HTML de la página o None si falla.
    """
    session = session or requests.Session()
    cache_key = make_key(url)
    cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
    if cached:
        return cached

    for intento in range(HTTP_MAX_RETRIES):
        try:
            headers = _get_random_headers(search_context)
            resp = session.get(
                url,
                headers=headers,
                timeout=HTTP_TIMEOUT,
                allow_redirects=True,
            )

            if resp.status_code == 429:
                if progress_callback:
                    progress_callback(f"⚠ Google limitó las peticiones (429). Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
                time.sleep(random.uniform(*HTTP_RETRY_DELAY) * (intento + 1))
                continue

            if resp.status_code != 200:
                if progress_callback:
                    progress_callback(f"⚠ Respuesta HTTP {resp.status_code}. Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
                time.sleep(random.uniform(*HTTP_RETRY_DELAY))
                continue

            html = resp.text
            html_lower = html.lower()
            if "captcha" in html_lower or "unusual traffic" in html_lower or "tráfico inusual" in html_lower:
                if progress_callback:
                    progress_callback(f"⚠ Google detectó tráfico automatizado. Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
                time.sleep(random.uniform(*HTTP_RETRY_DELAY) * (intento + 2))
                continue

            set_text(CACHE_DIR, cache_key, html, status=resp.status_code)
            return html

        except requests.exceptions.Timeout:
            if progress_callback:
                progress_callback(f"⚠ Timeout. Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
            time.sleep(random.uniform(*HTTP_RETRY_DELAY))
        except requests.exceptions.RequestException as e:
            if progress_callback:
                progress_callback(f"⚠ Error de red: {e}. Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
            time.sleep(random.uniform(*HTTP_RETRY_DELAY))

    return None


def _fetch_autocomplete(
    query: str,
    search_context: dict | None = None,
    session: requests.Session | None = None,
) -> List[str]:
    """Obtiene sugerencias de autocompletado de Google."""
    contexto = _resolver_contexto(search_context)
    url = AUTOCOMPLETE_URL.format(
        lang=contexto["language_code"],
        country=contexto["country_code"],
        query=requests.utils.quote(query),
    )
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": (
            f"{contexto['language_code']}-{contexto['country_code'].upper()},"
            f"{contexto['language_code']};q=0.9"
        ),
    }
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
        if isinstance(data, list) and len(data) >= 2:
            return [limpiar_texto(s) for s in data[1] if s]
    except Exception as exc:
        logger.debug("Autocomplete fallback fallo para %s: %s", query, exc)
        pass
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Extracción de PAA via HTML SERP
# ─────────────────────────────────────────────────────────────────────────────

def _extraer_preguntas_paa_html(soup: BeautifulSoup) -> List[str]:
    """
    Extrae las preguntas PAA del HTML de la SERP parseado.
    Múltiples estrategias para adaptarse a los cambios de Google.
    """
    preguntas = []
    vistas = set()

    def _agregar(texto: str):
        texto = limpiar_texto(texto)
        key = dedupe_key(texto)
        if texto and key and len(texto) >= 10 and len(texto) <= 200 and key not in vistas:
            if len(texto.split()) >= 3:
                vistas.add(key)
                preguntas.append(texto)

    # Estrategia 1: data-sgrd
    for container in soup.select("div[data-sgrd]"):
        for btn in container.select("div[role='button'], [data-q], span"):
            _agregar(btn.get_text(separator=" ", strip=True))

    # Estrategia 2: related-question-pair
    for par in soup.select("div.related-question-pair"):
        elem = par.select_one("div[role='button']") or par.select_one("span")
        if elem:
            _agregar(elem.get_text(separator=" ", strip=True))

    # Estrategia 3: data-q attribute
    for elem in soup.select("[data-q]"):
        _agregar(elem.get("data-q", ""))

    # Estrategia 4: jsname='yEVEwb'
    for cont in soup.select("div[jsname='yEVEwb']"):
        for btn in cont.select("div[role='button']"):
            _agregar(btn.get_text(separator=" ", strip=True))

    # Estrategia 5: aria-expanded (acordeones de PAA)
    for exp in soup.select("div[aria-expanded]"):
        _agregar(exp.get_text(separator=" ", strip=True))

    # Estrategia 6: Buscar JSON-LD o scripts con datos de PAA embebidos
    for script in soup.select("script"):
        text = script.string or ""
        if "related" in text.lower() and "question" in text.lower():
            # Intentar parsear como JSON
            try:
                # Buscar patrones JSON con preguntas
                import re
                matches = re.findall(r'"question"\s*:\s*"([^"]+)"', text, re.IGNORECASE)
                for m in matches:
                    _agregar(m)
            except Exception:
                pass

    return preguntas


# ─────────────────────────────────────────────────────────────────────────────
# Extracción de PAA via Autocomplete (fallback potente)
# ─────────────────────────────────────────────────────────────────────────────

def _extraer_preguntas_paa_autocomplete(
    keyword: str,
    progress_callback=None,
    search_context: dict | None = None,
    session: requests.Session | None = None,
) -> List[str]:
    """
    Extrae preguntas tipo PAA usando el autocompletado de Google.
    
    Técnica: buscar 'keyword + palabra_interrogativa' genera las mismas
    preguntas que aparecen en el bloque PAA de la SERP.
    """
    preguntas = []
    vistas = set()

    # Patrones que generan preguntas tipo PAA
    patrones_paa = [
        # Preguntas directas con la keyword
        "{keyword} qué",
        "{keyword} cómo",
        "{keyword} por qué",
        "{keyword} cuándo",
        "{keyword} dónde",
        "{keyword} quién",
        "{keyword} cuál",
        "{keyword} cuánto",
        # Preguntas inversas
        "qué es {keyword}",
        "cómo funciona {keyword}",
        "para qué sirve {keyword}",
        "por qué es importante {keyword}",
        "cuál es el mejor {keyword}",
        "cómo hacer {keyword}",
        "dónde encontrar {keyword}",
        "cuánto cuesta {keyword}",
        # Comparaciones y alternativas
        "{keyword} vs",
        "{keyword} o ",
        "{keyword} mejor",
        "{keyword} alternativa",
        # Problemas y soluciones
        "{keyword} problema",
        "{keyword} solución",
        "{keyword} error",
        "{keyword} no funciona",
        # Opiniones
        "{keyword} es bueno",
        "{keyword} es seguro",
        "{keyword} vale la pena",
        "{keyword} funciona",
    ]

    total = len(patrones_paa)
    for i, patron in enumerate(patrones_paa):
        query = patron.format(keyword=keyword)
        sugerencias = _fetch_autocomplete(query, search_context, session=session)

        for s in sugerencias:
            key = dedupe_key(s)
            if key and key not in vistas and len(s) >= 10:
                vistas.add(key)
                preguntas.append(s)

        time.sleep(random.uniform(0.1, 0.25))

    return preguntas


# ─────────────────────────────────────────────────────────────────────────────
# Extracción de búsquedas relacionadas
# ─────────────────────────────────────────────────────────────────────────────

def _extraer_busquedas_relacionadas_html(soup: BeautifulSoup) -> List[str]:
    """Extrae búsquedas relacionadas del HTML de la SERP."""
    relacionadas = []
    vistas = set()

    selectores = [
        "div.s75CSd a",
        "a.k8XOCe",
        "div.AJLUJb a",
        "div#botstuff a",
        "div.y6Uyqe a",
        "div[data-z] a",
        "div.oIk2Cb a",
    ]

    filtros = {"siguiente", "anterior", "next", "previous",
               "más resultados", "more results", "iniciar sesión",
               "sign in", "google", ""}
    filtros_norm = {dedupe_key(item) for item in filtros if item is not None}

    for selector in selectores:
        try:
            for elem in soup.select(selector):
                texto = limpiar_texto(elem.get_text(strip=True))
                key = dedupe_key(texto)
                if texto and key and len(texto) > 3 and key not in vistas and key not in filtros_norm:
                    vistas.add(key)
                    relacionadas.append(texto)
        except Exception:
            continue

    return relacionadas


def _extraer_people_also_search_for_html(soup: BeautifulSoup) -> List[str]:
    relacionadas = []
    vistas = set()

    patrones = [
        re.compile(r"people also search for", re.IGNORECASE),
        re.compile(r"otras personas tambi[eé]n buscan", re.IGNORECASE),
    ]

    contenedores = []
    for patron in patrones:
        contenedores.extend(soup.find_all(string=patron))

    candidatos = []
    for texto in contenedores:
        parent = getattr(texto, "parent", None)
        if not parent:
            continue
        candidatos.append(parent)

    for elem in candidatos:
        for a in elem.find_all_next("a", limit=40):
            texto = limpiar_texto(a.get_text(strip=True))
            if not texto or len(texto) < 3:
                continue
            key = dedupe_key(texto)
            if not key or key in vistas:
                continue
            href = a.get("href") or ""
            if "/search" not in href:
                continue
            vistas.add(key)
            relacionadas.append(texto)

    return relacionadas


def _extraer_busquedas_relacionadas_autocomplete(
    keyword: str,
    search_context: dict | None = None,
    session: requests.Session | None = None,
) -> List[str]:
    """Extrae búsquedas relacionadas usando autocompletado."""
    relacionadas = []
    vistas = set()
    vistas.add(dedupe_key(keyword))

    # Buscar variaciones con sufijos comunes
    sufijos = [
        " a", " b", " c", " d", " e",
        " para", " en", " de", " con", " sin",
        " mejor", " nuevo", " gratis", " online",
        " 2025", " 2026",
    ]

    for suf in sufijos:
        query = f"{keyword}{suf}"
        sugerencias = _fetch_autocomplete(query, search_context, session=session)

        for s in sugerencias:
            key = dedupe_key(s)
            if key and key not in vistas and key != dedupe_key(keyword):
                vistas.add(key)
                relacionadas.append(s)

        time.sleep(random.uniform(0.05, 0.15))

    return relacionadas


# ─────────────────────────────────────────────────────────────────────────────
# Función principal
# ─────────────────────────────────────────────────────────────────────────────

def _generar_variantes_serp(keyword: str) -> List[str]:
    if not SERP_DEEP_MODE:
        return [keyword]

    candidatos = [keyword]
    candidatos.extend([f"{mod}{keyword}" for mod in QUESTION_MODIFIERS])
    candidatos.extend([f"{keyword}{suf}" for suf in SEARCH_SUFFIXES])

    variantes = []
    vistas = set()
    limite = max(1, int(SERP_QUERY_VARIANT_LIMIT))
    for item in candidatos:
        key = dedupe_key(item)
        if key and key not in vistas:
            vistas.add(key)
            variantes.append(item)
        if len(variantes) >= limite:
            break
    return variantes


def scrape_google(keyword: str, progress_callback=None, search_context: dict | None = None) -> Dict[str, List[str]]:
    """
    Realiza una búsqueda en Google y extrae preguntas PAA y búsquedas relacionadas.

    Usa peticiones HTTP puras — NO abre ningún navegador.
    Combina parsing de HTML de la SERP con autocompletado inteligente.

    Args:
        keyword: Palabra clave a buscar.
        progress_callback: Función opcional para reportar progreso.

    Returns:
        Diccionario con:
        - "preguntas_paa": Lista de preguntas frecuentes
        - "busquedas_relacionadas": Lista de búsquedas relacionadas
    """
    resultado = {
        "preguntas_paa": [],
        "busquedas_relacionadas": [],
    }

    if progress_callback:
        progress_callback("Consultando SERP de Google via HTTP...")

    contexto = _resolver_contexto(search_context)
    paa_html = []
    rel_html = []
    vistas_paa_html = set()
    vistas_rel_html = set()
    seen_request_keys = set()
    session = requests.Session()

    variantes = _generar_variantes_serp(keyword)
    modos_tbm = SERP_TBM_MODES or [""]

    total_pages = max(1, int(SERP_PAGES))
    for q_index, query in enumerate(variantes):
        for tbm in modos_tbm:
            for page_index in range(total_pages):
                start = page_index * int(SERP_NUM_RESULTS)
                url = GOOGLE_SEARCH_URL.format(
                    query=requests.utils.quote(query),
                    lang=contexto["language_code"],
                    country=contexto["country_code"],
                    num=int(SERP_NUM_RESULTS),
                    start=start,
                )
                if tbm:
                    url = f"{url}&tbm={requests.utils.quote(tbm)}"

                if progress_callback:
                    etiqueta_tbm = f" | tbm={tbm}" if tbm else ""
                    etiqueta_var = f" | variante {q_index + 1}/{len(variantes)}" if len(variantes) > 1 else ""
                    progress_callback(
                        f"Consultando SERP pagina {page_index + 1}/{total_pages}{etiqueta_var}{etiqueta_tbm}..."
                    )

                request_key = make_key(url)
                if request_key in seen_request_keys:
                    continue
                seen_request_keys.add(request_key)

                html = _hacer_request(url, progress_callback, search_context, session=session)
                if not html:
                    continue

                if progress_callback:
                    progress_callback("Parseando HTML de la SERP...")
                soup = BeautifulSoup(html, "lxml")
                page_paa = _extraer_preguntas_paa_html(soup)
                page_rel = _extraer_busquedas_relacionadas_html(soup)
                page_rel.extend(_extraer_people_also_search_for_html(soup))

                for item in page_paa:
                    key = dedupe_key(item)
                    if key and key not in vistas_paa_html:
                        vistas_paa_html.add(key)
                        paa_html.append(item)

                for item in page_rel:
                    key = dedupe_key(item)
                    if key and key not in vistas_rel_html:
                        vistas_rel_html.add(key)
                        rel_html.append(item)

                if SERP_DEEP_MODE:
                    time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))
                elif page_index < total_pages - 1:
                    time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

    if paa_html and progress_callback:
        progress_callback(f"✅ {len(paa_html)} preguntas PAA extraídas del HTML (multi-página)")
    if rel_html and progress_callback:
        progress_callback(f"✅ {len(rel_html)} búsquedas relacionadas del HTML (multi-página)")

    # ─── Paso 2: Complementar con autocompletado inteligente ────────────
    if progress_callback:
        progress_callback("Extrayendo preguntas PAA via autocompletado...")

    paa_auto = _extraer_preguntas_paa_autocomplete(
        keyword,
        progress_callback,
        search_context,
        session=session,
    )

    # Combinar resultados (HTML primero, luego autocompletado sin duplicados)
    vistas_paa = {dedupe_key(p) for p in paa_html if dedupe_key(p)}
    todas_paa = list(paa_html)  # Copiar las de HTML
    for p in paa_auto:
        key = dedupe_key(p)
        if key and key not in vistas_paa:
            vistas_paa.add(key)
            todas_paa.append(p)

    resultado["preguntas_paa"] = todas_paa

    # ─── Paso 3: Búsquedas relacionadas ─────────────────────────────────
    if progress_callback:
        progress_callback("Extrayendo búsquedas relacionadas...")

    rel_auto = _extraer_busquedas_relacionadas_autocomplete(keyword, search_context, session=session)

    # Combinar
    vistas_rel = {dedupe_key(r) for r in rel_html if dedupe_key(r)}
    todas_rel = list(rel_html)
    for r in rel_auto:
        key = dedupe_key(r)
        if key and key not in vistas_rel:
            vistas_rel.add(key)
            todas_rel.append(r)

    resultado["busquedas_relacionadas"] = todas_rel

    if progress_callback:
        n_paa = len(resultado["preguntas_paa"])
        n_rel = len(resultado["busquedas_relacionadas"])
        progress_callback(f"✅ Extracción completa: {n_paa} preguntas PAA, {n_rel} relacionadas")

    return resultado
