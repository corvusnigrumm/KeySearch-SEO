"""
Módulo para obtener sugerencias de autocompletado de Google.

Usa el endpoint semi-público de Google Suggest que devuelve JSON
con las sugerencias que aparecen al escribir en la barra de búsqueda.

También genera preguntas frecuentes combinando la keyword con
prefijos de preguntas comunes en español.
"""

import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import (
    ALPHABET_EXPANSION,
    AUTOCOMPLETE_ALPHABET_LIMIT,
    AUTOCOMPLETE_DEEP_EXPANSION_LIMIT,
    AUTOCOMPLETE_DEEP_MAX_DELAY,
    AUTOCOMPLETE_DEEP_MIN_DELAY,
    AUTOCOMPLETE_PAA_RECURSIVE_DEPTH,
    CACHE_DIR,
    COUNTRY,
    HTTP_CACHE_TTL_SECONDS,
    LANG,
    QUESTION_MODIFIERS,
    SCRAPE_PROFILE,
    USER_AGENT_PROFILES,
)
from scraper.http_cache import get_text, make_key, set_text
from scraper.utils import dedupe_key, es_relevante_riguroso, limpiar_texto

# ─── Filtro de marcas comerciales para evitar contaminacion en expansion recursiva ───
# Si la keyword_base NO menciona una de estas marcas y la sugerencia SI la menciona,
# la sugerencia puede pasar como resultado pero NO puede ser semilla recursiva.
_MARCAS_NO_SEED = {
    "claro",
    "movistar",
    "tigo",
    "etb",
    "une",
    "wom",
    "directv",
    "virgin",
    "netflix",
    "spotify",
    "amazon",
    "apple",
    "samsung",
    "huawei",
    "xiaomi",
    "mercadolibre",
    "rappi",
    "uber",
    "didi",
    "cabify",
    "ifood",
    "bancolombia",
    "davivienda",
    "bbva",
    "nequi",
    "daviplata",
}


def _es_semilla_valida(sugerencia: str, keyword_base: str) -> bool:
    """Devuelve False si la sugerencia contiene una marca comercial que NO esta
    en la keyword base. Tales sugerencias no deben usarse como semillas
    recursivas porque generan cadenas completas de resultados de marca."""
    sug_lower = sugerencia.lower()
    kb_lower = keyword_base.lower()
    for marca in _MARCAS_NO_SEED:
        if marca in sug_lower and marca not in kb_lower:
            return False
    return True


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

    # Probamos varios 'clients' porque algunos son más permisivos que otros
    endpoints = [
        "https://suggestqueries.google.com/complete/search?client=chrome&hl={lang}&gl={country}&q={query}",
        "https://suggestqueries.google.com/complete/search?client=firefox&hl={lang}&gl={country}&q={query}",
        "https://www.google.com/complete/search?client=psy-ab&hl={lang}&gl={country}&q={query}",
        "https://suggestqueries.google.com/complete/search?client=psy&hl={lang}&gl={country}&q={query}",
        "https://www.google.com/complete/search?client=chrome&hl={lang}&q={query}",
    ]

    session = session or requests.Session()

    for url_template in endpoints:
        url = url_template.format(
            lang=lang,
            country=contexto["country_code"],
            query=requests.utils.quote(query),
        )

        perfil = random.choice(USER_AGENT_PROFILES)
        headers = {
            "User-Agent": perfil["ua"],
            "Accept": "*/*",
            "Accept-Language": f"{lang}-{country},{lang};q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "X-Requested-With": "XMLHttpRequest",
        }
        headers = {k: v for k, v in headers.items() if v}

        try:
            cache_key = make_key(url)
            cached = get_text(CACHE_DIR, cache_key, HTTP_CACHE_TTL_SECONDS)
            if cached:
                try:
                    data = json.loads(cached)
                    if isinstance(data, list) and len(data) >= 2:
                        return [limpiar_texto(s) for s in data[1] if isinstance(s, str)]
                except:
                    pass

            resp = session.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                # Algunos endpoints devuelven JSON con basura al inicio o formatos raros
                content = resp.text
                if content.startswith("window.google.ac.h("):
                    content = content[content.find("(") + 1 : content.rfind(")")]

                try:
                    data = json.loads(content)
                except:
                    # Fallback si no es JSON puro
                    continue

                set_text(CACHE_DIR, cache_key, json.dumps(data), status=200)

                # Detectar formato
                if isinstance(data, list) and len(data) >= 2:
                    suggestions = data[1]
                    if not suggestions:
                        return []

                    extracted = []
                    for s in suggestions:
                        if isinstance(s, str):
                            extracted.append(limpiar_texto(s))
                        elif isinstance(s, list) and s and isinstance(s[0], str):
                            extracted.append(limpiar_texto(s[0]))
                        elif isinstance(s, dict):
                            phrase = s.get("phrase") or s.get("q") or s.get("suggestion")
                            if phrase:
                                extracted.append(limpiar_texto(phrase))

                    if extracted:
                        return extracted

                continue
            elif resp.status_code == 429:
                continue
        except Exception:
            continue

    return []


from scraper.multi_engine_suggest import fetch_multi_engine_suggestions


def get_autocomplete_suggestions(
    keyword: str,
    expandir: bool = True,
    search_context: dict | None = None,
    engines: list[str] | None = None,
) -> list[str]:
    """
    Obtiene sugerencias de autocompletado para una palabra clave consultando
    múltiples motores en tiempo real (Google, YouTube, Amazon, Bing, DuckDuckGo).

    Args:
        keyword: Palabra clave a buscar.
        expandir: Si True, también busca con prefijos de preguntas y variaciones.
        search_context: Idioma y país seleccionados.
        engines: Lista opcional de motores a incluir.

    Returns:
        Lista de sugerencias únicas (sin duplicados).
    """
    todas = []
    vistas = set()
    session = requests.Session()
    ctx = _resolver_contexto(search_context)

    def _agregar(sugerencias: list[str]):
        for s in sugerencias:
            if not es_relevante_riguroso(keyword, s):
                continue
            key = dedupe_key(s)
            if key and key not in vistas:
                vistas.add(key)
                todas.append(s)

    # 1. Búsqueda Multi-Motor principal
    try:
        multi_res = fetch_multi_engine_suggestions(
            keyword=keyword,
            lang=ctx["language_code"],
            country=ctx["country_code"],
            engines=engines,
        )
        if multi_res:
            _agregar(list(multi_res.keys()))
    except Exception as e:
        logger.debug("Error en fetch_multi_engine_suggestions: %s", e)

    # Si por alguna razón no devolvió, asegurar Google directo
    if not todas:
        _agregar(_fetch_suggestions(keyword, search_context, session=session))

    if expandir:
        # 2. Expansión por modificadores de preguntas y comparativas multi-motor (paralelo)
        modificadores_clave = QUESTION_MODIFIERS + [" vs ", " precio ", " opiniones ", " comprar ", " mejor "]
        mods_to_use = modificadores_clave[: 12 if _perfil_extremo(search_context) else 6]

        def _fetch_modifier(mod):
            q_mod = f"{mod}{keyword}" if not mod.startswith(" ") else f"{keyword}{mod}"
            results = []
            try:
                m_res = fetch_multi_engine_suggestions(
                    q_mod, lang=ctx["language_code"], country=ctx["country_code"], engines=engines
                )
                if m_res:
                    results.extend(list(m_res.keys()))
            except Exception:
                pass
            results.extend(_fetch_suggestions(q_mod, search_context, session=session))
            return results

        with ThreadPoolExecutor(max_workers=min(4, len(mods_to_use))) as executor:
            futures = {executor.submit(_fetch_modifier, mod): mod for mod in mods_to_use}
            for future in as_completed(futures):
                try:
                    _agregar(future.result())
                except Exception:
                    pass

        # 3. Expansión Alfabética (a-z) multi-motor (paralelo)
        limite_alfabeto = len(ALPHABET_EXPANSION) if _perfil_extremo(search_context) else AUTOCOMPLETE_ALPHABET_LIMIT
        letters_to_use = ALPHABET_EXPANSION[:limite_alfabeto]

        def _fetch_letter(letra):
            q_letra = f"{keyword} {letra}"
            results = []
            try:
                m_res = fetch_multi_engine_suggestions(
                    q_letra, lang=ctx["language_code"], country=ctx["country_code"], engines=engines
                )
                if m_res:
                    results.extend(list(m_res.keys()))
            except Exception:
                pass
            results.extend(_fetch_suggestions(q_letra, search_context, session=session))
            return results

        with ThreadPoolExecutor(max_workers=min(6, len(letters_to_use))) as executor:
            futures = {executor.submit(_fetch_letter, letra): letra for letra in letters_to_use}
            for future in as_completed(futures):
                try:
                    _agregar(future.result())
                except Exception:
                    pass

    # 4. Modo Extremo Ultra-Profundo: rondas recursivas multi-motor sobre las mejores semillas
    if _perfil_extremo(search_context) and todas:
        factor = 2.5
        profundidad = max(2, int(AUTOCOMPLETE_PAA_RECURSIVE_DEPTH * factor))
        limite = max(10, int(AUTOCOMPLETE_DEEP_EXPANSION_LIMIT * factor))
        semillas = [s for s in todas if _es_semilla_valida(s, keyword)][:limite]

        for r_idx in range(profundidad):
            nuevas = []
            for semilla in semillas:
                # Consultar multi-motor para cada semilla
                try:
                    m_res = fetch_multi_engine_suggestions(
                        semilla, lang=ctx["language_code"], country=ctx["country_code"], engines=engines
                    )
                    if m_res:
                        _agregar(list(m_res.keys()))
                        nuevas.extend(list(m_res.keys()))
                except Exception:
                    pass

                sugerencias_extra = _fetch_suggestions(semilla, search_context, session=session)
                for s in sugerencias_extra:
                    if not es_relevante_riguroso(keyword, s):
                        continue
                    key = dedupe_key(s)
                    if key and key not in vistas:
                        vistas.add(key)
                        todas.append(s)
                        nuevas.append(s)

            if not nuevas:
                break
            semillas = [s for s in nuevas if _es_semilla_valida(s, keyword)][:limite]

    return todas


def get_question_suggestions(keyword: str, search_context: dict | None = None) -> list[str]:
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
        prefijos_preguntas.extend(
            [
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
            ]
        )

    for prefijo in prefijos_preguntas:
        query = f"{prefijo}{keyword}"
        sugerencias = _fetch_suggestions(query, search_context, session=session)
        for s in sugerencias:
            if not es_relevante_riguroso(keyword, s):
                continue
            key = dedupe_key(s)
            if key and key not in vistas:
                vistas.add(key)
                preguntas.append(s)
        time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))

    # Expansion recursiva para no dejar preguntas sin descubrir.
    # CRITICO: solo usar como semillas preguntas que no introduzcan marcas comerciales,
    # de lo contrario se generan cadenas enteras de preguntas de marca (Claro, Movistar, etc.)
    extra_factor = 2 if _perfil_extremo(search_context) else 1
    profundidad = max(1, int(AUTOCOMPLETE_PAA_RECURSIVE_DEPTH)) * extra_factor
    limite_semillas = max(1, int(AUTOCOMPLETE_DEEP_EXPANSION_LIMIT)) * extra_factor
    # Filtrar semillas iniciales: excluir las que introducen marcas no presentes en el keyword
    semillas = [p for p in preguntas[: limite_semillas * 3] if _es_semilla_valida(p, keyword)][:limite_semillas]
    for _ in range(profundidad):
        nuevas = []
        for semilla in semillas:
            sugerencias = _fetch_suggestions(semilla, search_context, session=session)
            for s in sugerencias:
                if not es_relevante_riguroso(keyword, s):
                    continue
                key = dedupe_key(s)
                if key and key not in vistas:
                    vistas.add(key)
                    preguntas.append(s)
                    nuevas.append(s)
            time.sleep(random.uniform(AUTOCOMPLETE_DEEP_MIN_DELAY, AUTOCOMPLETE_DEEP_MAX_DELAY))
        if not nuevas:
            break
        # Filtrar semillas del siguiente ciclo tambien
        semillas = [s for s in nuevas[: limite_semillas * 3] if _es_semilla_valida(s, keyword)][:limite_semillas]

    return preguntas
