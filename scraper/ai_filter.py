import json
import logging
import re
import requests

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

# Marcas comerciales / operadores / ISPs conocidos que contaminan resultados
# cuando NO son parte de la keyword_base buscada por el usuario.
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

# Máximo de keywords por llamada a Groq para no saturar el contexto
_BATCH_SIZE = 40


def _post_groq_json(prompt: str, timeout: int = 40):
    """Invoca Groq y devuelve contenido JSON parseado o None."""
    if not GROQ_API_KEY:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": (
                "Eres una API JSON estricta. Devuelves UNICAMENTE JSON valido, "
                "sin markdown, sin texto extra, sin explicaciones."
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        # Limpiar posibles bloques markdown que el modelo a veces incluye
        if content.startswith("```json"):
            content = content[7:]
            if "```" in content:
                content = content[:content.rfind("```")]
            content = content.strip()
        elif content.startswith("```"):
            content = content[3:]
            if "```" in content:
                content = content[:content.rfind("```")]
            content = content.strip()
        return json.loads(content)
    except Exception as e:
        logger.warning("Error en llamada Groq JSON: %s", e)
        return None


def _filtro_determinista(keywords: list[str], keyword_base: str) -> list[str]:
    """
    Pre-filtro rápido sin IA:
    1. Elimina keywords con marcas comerciales cuando la marca NO está en keyword_base.
    2. Elimina patrones SEO-inútiles (para colorear, juegos, dibujos, etc.).
    """
    kb_lower = keyword_base.lower()
    resultado = []
    for kw in keywords:
        kw_lower = kw.lower()

        # Comprobar si hay una marca comercial en la sugerencia que NO está en la keyword base
        marca_encontrada = False
        for marca in _MARCAS_COMERCIALES:
            if marca in kw_lower and marca not in kb_lower:
                # Si la keyword base contiene la marca, es legítimo. Si no, es contaminación.
                marca_encontrada = True
                break
        if marca_encontrada:
            logger.debug("Filtro determinista eliminó (marca): %s", kw)
            continue

        # Eliminar patrones SEO-inútiles
        patron_inutil = False
        for patron in _PATRONES_SEO_INUTILES:
            if re.search(patron, kw_lower):
                patron_inutil = True
                break
        if patron_inutil:
            logger.debug("Filtro determinista eliminó (patrón SEO inútil): %s", kw)
            continue

        resultado.append(kw)
    return resultado


def _filtrar_lote_con_ia(lote: list[str], keyword_base: str, pais: str) -> list[str]:
    """
    Filtra un lote de keywords (máx. _BATCH_SIZE) con una sola llamada a Groq.
    Prompt en dos etapas explícitas: geo + SEO editorial.
    """
    prompt = (
        f"Eres un analista SEO SENIOR para un medio digital en {pais}. "
        f"Analiza esta lista de keywords encontradas a partir de: '{keyword_base}'.\n\n"
        f"TAREA: Filtra con criterio ESTRICTO. Elimina una keyword si cumple AL MENOS UNO de estos criterios:\n"
        f"\n"
        f"[CRITERIO GEO] Menciona explícitamente otro país, ciudad o región distinta a {pais}. "
        f"Ejemplos de eliminación inmediata: 'en mexico', 'en venezuela', 'en argentina', 'en peru', "
        f"'en chile', 'en españa', 'en bogota si el pais es mexico', etc.\n"
        f"\n"
        f"[CRITERIO SEO] No tiene valor editorial real para un redactor SEO que escribe sobre '{keyword_base}'. "
        f"Ejemplos de eliminación: contenido para niños ('para colorear', 'dibujos'), "
        f"marcas comerciales específicas que no son el tema principal, "
        f"contenido de entretenimiento sin relación temática.\n"
        f"\n"
        f"[CRITERIO MARCA] Si '{keyword_base}' NO contiene nombre de empresa/marca/operador, "
        f"elimina cualquier keyword que introduzca una marca comercial específica "
        f"(ej: Claro, Movistar, Tigo, Nequi, Bancolombia, Rappi, etc.). "
        f"Si la keyword base SÍ es una marca, entonces keywords de esa misma marca son válidas.\n"
        f"\n"
        f"IMPORTANTE: Si tienes duda, CONSERVA la keyword. Solo elimina lo que claramente no cumple.\n"
        f"\n"
        f"Responde ÚNICAMENTE con un JSON Array de strings con las keywords que PASARON el filtro.\n"
        f"Ejemplo de respuesta válida: [\"keyword a\", \"keyword b\"]\n\n"
        f"Lista a filtrar:\n"
        f"{json.dumps(lote, ensure_ascii=False)}"
    )

    try:
        filtered = _post_groq_json(prompt, timeout=35)
        if isinstance(filtered, list):
            original_set = set(lote)
            return [kw for kw in filtered if kw in original_set]
        return lote
    except Exception as e:
        logger.warning("Error en filtro IA de lote: %s", e)
        return lote


def filtrar_con_ia(keywords: list[str], keyword_base: str, pais: str) -> list[str]:
    """
    Pipeline completo de filtrado:
    1. Pre-filtro determinista rápido (marcas, patrones inútiles)
    2. Filtro IA por lotes de _BATCH_SIZE keywords (geo + SEO editorial)

    Si hay algún error en la IA, se devuelve el resultado del pre-filtro.
    Si no hay API key, solo aplica el pre-filtro determinista.
    """
    if not keywords:
        return keywords

    # Paso 1: filtro rápido sin IA
    pre_filtradas = _filtro_determinista(keywords, keyword_base)
    logger.info(
        "Pre-filtro determinista: %d → %d keywords (eliminadas %d)",
        len(keywords), len(pre_filtradas), len(keywords) - len(pre_filtradas)
    )

    if not GROQ_API_KEY or not pre_filtradas:
        return pre_filtradas

    # Paso 2: filtro IA por lotes
    resultado_final = []
    for i in range(0, len(pre_filtradas), _BATCH_SIZE):
        lote = pre_filtradas[i: i + _BATCH_SIZE]
        lote_filtrado = _filtrar_lote_con_ia(lote, keyword_base, pais)
        resultado_final.extend(lote_filtrado)
        logger.info(
            "Lote IA %d-%d: %d → %d",
            i + 1, i + len(lote), len(lote), len(lote_filtrado)
        )

    return resultado_final


def generar_bloques_editoriales(
    keyword_base: str,
    pais: str,
    top_autocomplete: list[str],
    top_paa: list[str],
    top_preguntas_autocomplete: list[str],
    top_relacionadas: list[str],
    top_keywords_trends: list[str] = None,
) -> dict:
    """
    Genera bloques editoriales para la plantilla de informe.
    Devuelve un dict con claves:
      - ejes (9 ejes estrategicos)
      - propuesta (1 linea)
      - enfoque (parrafo corto)
      - titulos (10 titulos SEO)
      - subtitulos (10 subtitulos)
      - keywords_trends (10 keywords long-tail)

    Usa top 15 por fuente para analisis SEO profundo.
    """
    if top_keywords_trends is None:
        top_keywords_trends = []

    kw_trends = list(top_keywords_trends[:10])
    while len(kw_trends) < 10:
        kw_trends.append(f"{keyword_base} kw {len(kw_trends) + 1}")

    fallback = {
        "ejes": [
            f"Autocompletado: {top_autocomplete[0] if top_autocomplete else keyword_base}",
            f"Preguntas PAA: {top_paa[0] if top_paa else keyword_base}",
            f"Preguntas autocompletado: {top_preguntas_autocomplete[0] if top_preguntas_autocomplete else keyword_base}",
            f"Busquedas relacionadas: {top_relacionadas[0] if top_relacionadas else keyword_base}",
            f"Eje adicional 1 para {keyword_base}",
            f"Eje adicional 2 para {keyword_base}",
            f"Eje adicional 3 para {keyword_base}",
            f"Eje adicional 4 para {keyword_base}",
            f"Eje adicional 5 para {keyword_base}",
        ],
        "propuesta": f"Guia completa sobre {keyword_base}",
        "enfoque": f"Resolver dudas reales de usuarios en {pais} con enfoque comparativo y accionable.",
        "titulos": [f"{keyword_base} idea {i}" for i in range(1, 11)],
        "subtitulos": [f"Subtema {i} para {keyword_base}" for i in range(1, 11)],
        "keywords_trends": kw_trends,
    }

    if not GROQ_API_KEY:
        return fallback

    # Usar top 15 por fuente para un analisis SEO mas profundo y representativo
    ac_muestra = top_autocomplete[:15]
    paa_muestra = top_paa[:15]
    preg_ac_muestra = top_preguntas_autocomplete[:15]
    rel_muestra = top_relacionadas[:15]
    trends_muestra = top_keywords_trends[:20] if top_keywords_trends else []

    prompt = (
        "Eres un estratega SEO senior con 10 anos de experiencia en medios digitales hispanohablantes. "
        "Tu tarea es generar bloques editoriales ESTRATEGICOS Y PROFUNDOS para una plantilla de informe SEO "
        "que usaran redactores profesionales para planificar su contenido.\n\n"
        f"KEYWORD PRINCIPAL: '{keyword_base}'\n"
        f"PAIS OBJETIVO: '{pais}'\n\n"
        "EVIDENCIA REAL DE GOOGLE (lo que los usuarios REALMENTE buscan):\n"
        f"- Autocompletado (Top 15): {json.dumps(ac_muestra, ensure_ascii=False)}\n"
        f"- Preguntas PAA de la SERP (Top 15): {json.dumps(paa_muestra, ensure_ascii=False)}\n"
        f"- Preguntas por Autocompletado (Top 15): {json.dumps(preg_ac_muestra, ensure_ascii=False)}\n"
        f"- Busquedas relacionadas (Top 15): {json.dumps(rel_muestra, ensure_ascii=False)}\n"
        f"- Keywords con mayor volumen/tendencia (Top 20): {json.dumps(trends_muestra, ensure_ascii=False)}\n\n"
        "ANALISIS QUE DEBES REALIZAR:\n"
        "1. Identifica la INTENCION DE BUSQUEDA predominante: informacional, transaccional, navegacional o comparativa.\n"
        "2. Detecta los SUBTEMAS y ANGULOS mas recurrentes en la evidencia.\n"
        "3. Identifica BRECHAS DE CONTENIDO: preguntas frecuentes sin respuesta optima clara.\n"
        "4. Prioriza keywords con ALTA INTENSION EDITORIAL (no keywords de marca ni de contenido infantil).\n\n"
        "REGLAS CRITICAS - VIOLACION = RESPUESTA INVALIDA:\n"
        f"- NUNCA incluyas marcas comerciales especificas (Claro, Movistar, Tigo, Rappi, etc.) a menos que '{keyword_base}' sea exactamente esa marca.\n"
        "- NUNCA incluyas contenido infantil (colorear, juegos, canciones, dibujos, cuentos).\n"
        f"- NUNCA incluyas referencias a paises distintos a {pais}.\n"
        "- Cada titulo H1 debe tener intencion SEO clara y ser accionable para un redactor.\n"
        "- Los subtitulos son H2/H3 reales que estructuran el articulo (no vagues, no genericos).\n"
        "- keywords_trends: variaciones long-tail reales extraidas de la evidencia, priorizando las de mayor potencial editorial.\n\n"
        "Devuelve UNICAMENTE este JSON (sin markdown, sin texto adicional):\n"
        "{\n"
        '  "intencion_predominante": "informacional|transaccional|navegacional|comparativa",\n'
        '  "ejes": ["9 ejes tematicos estrategicos con angulo editorial concreto cada uno"],\n'
        '  "propuesta": "1 linea: tema central del articulo principal recomendado",\n'
        '  "enfoque": "2-3 oraciones: angulo editorial, tono recomendado e intension del usuario objetivo",\n'
        '  "titulos": ["10 titulos H1 variados en formato: preguntas, listas, guias, comparativas, how-to"],\n'
        '  "subtitulos": ["10 subtitulos H2/H3 que estructuran el articulo principal de forma logica"],\n'
        '  "keywords_trends": ["10 keywords long-tail de alta prioridad extraidas de la evidencia real"]\n'
        "}\n"
    )

    result = _post_groq_json(prompt, timeout=55)
    if not isinstance(result, dict):
        return fallback

    ejes = result.get("ejes") if isinstance(result.get("ejes"), list) else []
    titulos = result.get("titulos") if isinstance(result.get("titulos"), list) else []
    subtitulos = result.get("subtitulos") if isinstance(result.get("subtitulos"), list) else []
    keywords_trends = result.get("keywords_trends") if isinstance(result.get("keywords_trends"), list) else []
    propuesta = result.get("propuesta") if isinstance(result.get("propuesta"), str) else ""
    enfoque = result.get("enfoque") if isinstance(result.get("enfoque"), str) else ""

    merged = {
        "ejes": [str(x).strip() for x in (ejes[:9] if ejes else fallback["ejes"])],
        "propuesta": (propuesta or fallback["propuesta"]).strip(),
        "enfoque": (enfoque or fallback["enfoque"]).strip(),
        "titulos": [str(x).strip() for x in (titulos[:10] if titulos else fallback["titulos"])],
        "subtitulos": [str(x).strip() for x in (subtitulos[:10] if subtitulos else fallback["subtitulos"])],
        "keywords_trends": [str(x).strip() for x in (keywords_trends[:10] if keywords_trends else fallback["keywords_trends"])],
    }

    while len(merged["ejes"]) < 9:
        merged["ejes"].append(fallback["ejes"][len(merged["ejes"])])
    while len(merged["titulos"]) < 10:
        merged["titulos"].append(fallback["titulos"][len(merged["titulos"])])
    while len(merged["subtitulos"]) < 10:
        merged["subtitulos"].append(fallback["subtitulos"][len(merged["subtitulos"])])
    while len(merged["keywords_trends"]) < 10:
        merged["keywords_trends"].append(fallback["keywords_trends"][len(merged["keywords_trends"])])

    return merged
