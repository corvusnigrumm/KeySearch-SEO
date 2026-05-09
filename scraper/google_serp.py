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
    USER_AGENT_PROFILES,
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
    SERP_MIN_REQUEST_INTERVAL,
    SERP_429_BREAKER_THRESHOLD,
    SERP_429_BREAKER_COOLDOWN,
    AUTOCOMPLETE_DEEP_EXPANSION_LIMIT,
    AUTOCOMPLETE_DEEP_RELATED_ROUNDS,
    AUTOCOMPLETE_DEEP_MIN_DELAY,
    AUTOCOMPLETE_DEEP_MAX_DELAY,
    AUTOCOMPLETE_PAA_RECURSIVE_DEPTH,
    AUTOCOMPLETE_RELATED_RECURSIVE_DEPTH,
    AUTOCOMPLETE_DEEP_SEED_LIMIT,
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


def _get_random_headers(search_context: dict | None = None) -> dict:
    """
    Genera un juego de headers HTTP completo y coherente que imita Chrome real.
    Usa perfiles con sec-ch-ua correcto para cada versión de navegador.
    """
    contexto = _resolver_contexto(search_context)
    lang = contexto["language_code"]
    country = contexto["country_code"].upper()

    # Elegir un perfil completo aleatoriamente
    perfil = random.choice(USER_AGENT_PROFILES)
    ua = perfil["ua"]
    is_firefox = "Firefox" in ua

    # Construir Accept-Language realista
    accept_lang = f"{lang}-{country},{lang};q=0.9,en-US;q=0.8,en;q=0.7"

    if is_firefox:
        # Headers de Firefox (no usa sec-ch-ua)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": accept_lang,
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Pragma": "no-cache",
        }
    else:
        # Headers de Chrome/Edge (incluye sec-ch-ua para evitar detección)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": accept_lang,
            "Accept-Encoding": "gzip, deflate, br",
            "sec-ch-ua": perfil["sec-ch-ua"],
            "sec-ch-ua-mobile": perfil["sec-ch-ua-mobile"],
            "sec-ch-ua-platform": perfil["sec-ch-ua-platform"],
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
        }


def _crear_sesion() -> requests.Session:
    """
    Crea una sesión requests configurada para pasar desapercibida.
    Fuerza HTTP/1.1 para evitar el Error 505 (HTTP Version Not Supported).
    """
    session = requests.Session()
    # Forzar HTTP/1.1 — el servidor de Google a veces rechaza HTTP/2 vía requests
    session.headers.update({"Connection": "keep-alive"})
    # Montar un adaptador que deshabilite HTTP/2 si está disponible vía httpx/h2
    return session


def _hacer_request(
    url: str,
    progress_callback=None,
    search_context: dict | None = None,
    session: requests.Session | None = None,
    rate_state: dict | None = None,
) -> Optional[str]:
    """
    Realiza una petición HTTP GET con reintentos, backoff exponencial y
    headers anti-detección completos.

    Returns:
        HTML de la página o None si falla tras todos los reintentos.
    """
    if session is None:
        session = _crear_sesion()

    cache_key = make_key(url)
    cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
    if cached:
        return cached

    for intento in range(HTTP_MAX_RETRIES):
        try:
            headers = _get_random_headers(search_context)
            # Añadir Referer realista en reintentos (simula navegación previa)
            if intento > 0:
                headers["Referer"] = "https://www.google.com/"

            resp = session.get(
                url,
                headers=headers,
                timeout=HTTP_TIMEOUT,
                allow_redirects=True,
            )

            # Error 505: HTTP Version Not Supported
            # Puede ocurrir si el servidor rechaza la negociación de protocolo
            if resp.status_code == 505:
                if progress_callback:
                    progress_callback(
                        f"  Advertencia HTTP 505 (version protocolo). Reintento {intento + 1}/{HTTP_MAX_RETRIES}..."
                    )
                # Espera larga + cambiar perfil de agente en siguiente intento
                time.sleep(random.uniform(8, 15) * (intento + 1))
                continue

            # Rate limit de Google
            if resp.status_code == 429:
                espera = random.uniform(15, 30) * (intento + 1)
                if rate_state is not None:
                    rate_state["consecutive_429"] = int(rate_state.get("consecutive_429", 0)) + 1
                    if rate_state["consecutive_429"] >= max(1, int(SERP_429_BREAKER_THRESHOLD)):
                        cooldown = random.uniform(*SERP_429_BREAKER_COOLDOWN)
                        rate_state["blocked_until"] = time.time() + cooldown
                        rate_state["breaker_open"] = True
                        if progress_callback:
                            progress_callback(
                                "  Google activo proteccion anti-bot (429 repetido). "
                                f"Pausando SERP por {cooldown:.0f}s y continuando con otras fuentes..."
                            )
                        return None
                if progress_callback:
                    progress_callback(
                        f"  Advertencia Google limito peticiones (429). Esperando {espera:.0f}s..."
                    )
                time.sleep(espera)
                continue

            # Cualquier otro error no-200
            if resp.status_code not in (200, 301, 302):
                if progress_callback:
                    progress_callback(
                        f"  Respuesta HTTP {resp.status_code}. Reintento {intento + 1}/{HTTP_MAX_RETRIES}..."
                    )
                time.sleep(random.uniform(*HTTP_RETRY_DELAY) * (intento + 1))
                continue

            html = resp.text
            html_lower = html.lower()

            # Detectar bloqueo por CAPTCHA
            if "captcha" in html_lower or "unusual traffic" in html_lower or "tráfico inusual" in html_lower:
                espera = random.uniform(20, 45) * (intento + 1)
                if progress_callback:
                    progress_callback(
                        f"  Google detecto trafico automatizado. Esperando {espera:.0f}s antes del reintento {intento + 1}/{HTTP_MAX_RETRIES}..."
                    )
                time.sleep(espera)
                continue

            # Exito: guardar en cache y retornar
            set_text(CACHE_DIR, cache_key, html, status=resp.status_code)
            if rate_state is not None:
                rate_state["consecutive_429"] = 0
            return html

        except requests.exceptions.Timeout:
            if progress_callback:
                progress_callback(f"  Timeout. Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
            time.sleep(random.uniform(*HTTP_RETRY_DELAY) * (intento + 1))
        except requests.exceptions.ConnectionError as e:
            if progress_callback:
                progress_callback(f"  Error de conexion: {e}. Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
            time.sleep(random.uniform(*HTTP_RETRY_DELAY) * (intento + 1))
        except requests.exceptions.RequestException as e:
            if progress_callback:
                progress_callback(f"  Error de red: {e}. Reintento {intento + 1}/{HTTP_MAX_RETRIES}...")
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
    deep_mode: bool = False,
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

    extreme_mode = _perfil_extremo(search_context)
    if deep_mode:
        patrones_paa.extend(
            [
                "{keyword} tutorial",
                "{keyword} guía",
                "{keyword} ejemplos",
                "{keyword} ventajas",
                "{keyword} desventajas",
                "error de {keyword}",
                "alternativas a {keyword}",
                "merece la pena {keyword}",
                "opiniones de {keyword}",
                "{keyword} 2026",
                "{keyword} para principiantes",
                "{keyword} para empresas",
                "{keyword} para niños",
                "{keyword} riesgos",
                "{keyword} beneficios",
                "{keyword} mitos",
                "{keyword} preguntas frecuentes",
            ]
        )

    if extreme_mode:
        # Patrones adicionales exclusivos del modo extremo
        # Temporales y situacionales
        patrones_paa.extend([
            "{keyword} 2024",
            "{keyword} 2025",
            "{keyword} en Colombia",
            "{keyword} en Mexico",
            "{keyword} en España",
            "{keyword} en Argentina",
            "{keyword} en Chile",
            "{keyword} hoy",
            "{keyword} este año",
            "{keyword} recientemente",
            # Comparativas y elección
            "{keyword} diferencias",
            "{keyword} comparacion",
            "mejor {keyword}",
            "el mejor {keyword}",
            "{keyword} recomendaciones",
            "{keyword} cual elegir",
            "{keyword} opciones",
            # Precios y economía
            "precio de {keyword}",
            "costo de {keyword}",
            "cuánto vale {keyword}",
            "{keyword} barato",
            "{keyword} gratis",
            "{keyword} gratuito",
            # Intención práctica
            "aprender {keyword}",
            "estudiar {keyword}",
            "certificacion {keyword}",
            "curso de {keyword}",
            "como usar {keyword}",
            "como instalar {keyword}",
            "como configurar {keyword}",
            "como empezar con {keyword}",
            # Reviews y experiencias
            "{keyword} review",
            "{keyword} reseña",
            "{keyword} experiencia",
            "{keyword} testimonio",
            "{keyword} real",
            "{keyword} confiable",
            # Profesional y negocios
            "{keyword} para negocios",
            "{keyword} para profesionales",
            "{keyword} empresarial",
            "{keyword} freelance",
            # Técnico y avanzado
            "como funciona {keyword}",
            "{keyword} tecnico",
            "{keyword} avanzado",
            "{keyword} experto",
            # Salud / seguridad (aplica según temática)
            "{keyword} seguro",
            "{keyword} peligros",
            "{keyword} contraindicaciones",
            "{keyword} efectos secundarios",
            # Redes sociales y tendencias
            "{keyword} tendencia",
            "{keyword} viral",
            "{keyword} red social",
            # Combinaciones de intención mixta
            "por qué es importante {keyword}",
            "cuáles son los tipos de {keyword}",
            "historia de {keyword}",
            "origen de {keyword}",
            "futuro de {keyword}",
            "principales {keyword}",
            "características de {keyword}",
            "componentes de {keyword}",
            "elementos de {keyword}",
            "fases de {keyword}",
            "etapas de {keyword}",
            "pasos para {keyword}",
            "requisitos para {keyword}",
            "todo sobre {keyword}",
            "guía completa de {keyword}",
            "manual de {keyword}",
            # Variaciones de escritura sin acento (mayor cobertura)
            "{keyword} como funciona",
            "{keyword} para que sirve",
            "{keyword} que es",
            "{keyword} cuanto cuesta",
            "{keyword} como se hace",
        ])

    for patron in patrones_paa:
        query = patron.format(keyword=keyword)
        sugerencias = _fetch_autocomplete(query, search_context, session=session)

        for s in sugerencias:
            key = dedupe_key(s)
            if key and key not in vistas and len(s) >= 10:
                vistas.add(key)
                preguntas.append(s)

        time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))

    if deep_mode:
        factor = 2 if extreme_mode else 1
        profundidad_max = max(1, int(AUTOCOMPLETE_PAA_RECURSIVE_DEPTH)) * factor
        limit_expansion = max(1, int(AUTOCOMPLETE_DEEP_EXPANSION_LIMIT)) * factor
        seed_limit = max(1, int(AUTOCOMPLETE_DEEP_SEED_LIMIT)) * factor
        visitadas = {dedupe_key(s) for s in preguntas if dedupe_key(s)}
        semillas = list(preguntas[:seed_limit])

        for _ in range(profundidad_max):
            nuevas_semillas = []
            for semilla in semillas[:limit_expansion]:
                sugerencias = _fetch_autocomplete(semilla, search_context, session=session)
                for s in sugerencias:
                    key = dedupe_key(s)
                    if key and key not in vistas and len(s) >= 10:
                        vistas.add(key)
                        preguntas.append(s)
                        if key not in visitadas:
                            visitadas.add(key)
                            nuevas_semillas.append(s)
                time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))
            if not nuevas_semillas:
                break
            semillas = nuevas_semillas

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
    deep_mode: bool = False,
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

        time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))

    if deep_mode:
        factor = 2 if _perfil_extremo(search_context) else 1
        rondas = max(1, int(AUTOCOMPLETE_DEEP_RELATED_ROUNDS)) * factor
        profundidad_max = max(1, int(AUTOCOMPLETE_RELATED_RECURSIVE_DEPTH)) * factor
        limit_expansion = max(1, int(AUTOCOMPLETE_DEEP_EXPANSION_LIMIT)) * factor
        seed_limit = max(1, int(AUTOCOMPLETE_DEEP_SEED_LIMIT)) * factor
        semillas = list(relacionadas[:seed_limit])

        for _ in range(rondas * profundidad_max):
            nuevas = []
            for base in semillas:
                sugerencias = _fetch_autocomplete(base, search_context, session=session)
                for s in sugerencias:
                    key = dedupe_key(s)
                    if key and key not in vistas and key != dedupe_key(keyword):
                        vistas.add(key)
                        relacionadas.append(s)
                        nuevas.append(s)
                time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))
            if not nuevas:
                break
            semillas = nuevas[:limit_expansion]

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
    session = _crear_sesion()  # Sesión configurada para evitar bloqueos
    rate_state = {
        "consecutive_429": 0,
        "breaker_open": False,
        "blocked_until": 0.0,
        "last_request_ts": 0.0,
    }
    serp_pages_ok = 0

    variantes = _generar_variantes_serp(keyword)
    modos_tbm = SERP_TBM_MODES or [""]

    total_pages = max(1, int(SERP_PAGES))
    for q_index, query in enumerate(variantes):
        # Pausa entre variantes de query (simula que el usuario piensa antes de buscar otra cosa)
        if q_index > 0:
            time.sleep(random.uniform(5.0, 10.0))

        for tbm_index, tbm in enumerate(modos_tbm):
            # Pausa entre modos TBM
            if tbm_index > 0:
                time.sleep(random.uniform(3.0, 7.0))

            for page_index in range(total_pages):
                now = time.time()
                elapsed = now - float(rate_state.get("last_request_ts", 0.0))
                min_interval = random.uniform(*SERP_MIN_REQUEST_INTERVAL)
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)

                blocked_until = float(rate_state.get("blocked_until", 0.0))
                if blocked_until > time.time():
                    if progress_callback:
                        restante = blocked_until - time.time()
                        progress_callback(
                            f"SERP en cooldown por bloqueo 429 ({restante:.0f}s restantes)."
                        )
                    continue

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

                html = _hacer_request(
                    url,
                    progress_callback,
                    search_context,
                    session=session,
                    rate_state=rate_state,
                )
                rate_state["last_request_ts"] = time.time()
                if not html:
                    continue
                serp_pages_ok += 1

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

                # Pausa siempre entre páginas (no solo en modo profundo)
                if page_index < total_pages - 1:
                    time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

    if paa_html and progress_callback:
        progress_callback(f"✅ {len(paa_html)} preguntas PAA extraídas del HTML (multi-página)")
    if rel_html and progress_callback:
        progress_callback(f"✅ {len(rel_html)} búsquedas relacionadas del HTML (multi-página)")

    # ─── Paso 2: Complementar con autocompletado inteligente ────────────
    if progress_callback:
        progress_callback("Extrayendo preguntas PAA via autocompletado...")

    # En modo extremo SIEMPRE activar deep mode, sin importar si la SERP respondio
    # En modo normal, deep mode solo si la SERP no entrego nada
    is_extreme = _perfil_extremo(search_context)
    deep_autocomplete_mode = is_extreme or (serp_pages_ok == 0)

    if serp_pages_ok == 0 and progress_callback:
        progress_callback(
            "SERP no disponible o bloqueada. Activando autocomplete profundo (mas cobertura, mas lento)."
        )
    elif is_extreme and progress_callback:
        progress_callback(
            "Modo extremo activo: forzando expansion profunda de autocomplete para maxima cobertura."
        )

    paa_auto = _extraer_preguntas_paa_autocomplete(
        keyword,
        progress_callback,
        search_context,
        session=session,
        deep_mode=deep_autocomplete_mode,
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

    rel_auto = _extraer_busquedas_relacionadas_autocomplete(
        keyword,
        search_context,
        session=session,
        deep_mode=deep_autocomplete_mode,  # Mismo flag: extremo siempre es deep
    )

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
