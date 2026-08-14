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


try:
    from groq import Groq
    _groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except Exception:
    _groq_client = None


def _limpiar_respuesta_json(raw_text: str) -> str:
    """Elimina etiquetas de razonamiento <think> y bloques markdown ```json."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    # Eliminar bloques de razonamiento si el modelo los emite
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    if text.startswith("```json"):
        text = text[7:]
        if "```" in text:
            text = text[:text.rfind("```")]
        text = text.strip()
    elif text.startswith("```"):
        text = text[3:]
        if "```" in text:
            text = text[:text.rfind("```")]
        text = text.strip()
    return text


def _post_groq_json(prompt: str, timeout: int = 45, model: str = None):
    """
    Invoca Groq utilizando el SDK oficial (soporta openai/gpt-oss-120b con reasoning_effort='medium'
    y Llama 3.3 70B) y devuelve contenido JSON parseado.
    """
    if not GROQ_API_KEY:
        return None

    target_model = model or GROQ_MODEL
    is_reasoning = ("gpt-oss" in target_model.lower() or "deepseek-r1" in target_model.lower())

    # 1. Intento con SDK oficial de Groq
    if _groq_client is not None:
        try:
            req_params = {
                "model": target_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Eres una API JSON estricta. Devuelves UNICAMENTE JSON valido, "
                            "sin etiquetas markdown, sin texto extra y sin explicaciones."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
            }

            if is_reasoning:
                req_params["temperature"] = 1
                req_params["max_completion_tokens"] = 2048
                req_params["top_p"] = 1
                if "gpt-oss" in target_model.lower():
                    req_params["reasoning_effort"] = "medium"
            else:
                req_params["temperature"] = 0.2
                req_params["max_tokens"] = 2048

            completion = _groq_client.chat.completions.create(**req_params)
            raw_content = completion.choices[0].message.content or ""
            clean_json = _limpiar_respuesta_json(raw_content)
            if clean_json:
                return json.loads(clean_json)
        except Exception as e:
            logger.warning("Error con SDK Groq (%s): %s. Intentando fallback...", target_model, e)
            # Fallback a llama-3.3-70b-versatile si el modelo solicitado falló
            if target_model != "llama-3.3-70b-versatile":
                try:
                    fallback_comp = _groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Devuelve UNICAMENTE JSON valido."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        max_tokens=2048
                    )
                    raw_content = fallback_comp.choices[0].message.content or ""
                    clean_json = _limpiar_respuesta_json(raw_content)
                    if clean_json:
                        return json.loads(clean_json)
                except Exception as fb_err:
                    logger.warning("Fallback SDK falló: %s", fb_err)

    # 2. Fallback por HTTP requests directo
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": "Devuelve UNICAMENTE JSON valido sin markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        clean_json = _limpiar_respuesta_json(raw_content)
        return json.loads(clean_json)
    except Exception as e:
        logger.warning("Error en llamada HTTP Groq JSON: %s", e)
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
        "ejes": ["" for _ in range(9)],
        "propuesta": "",
        "enfoque": "",
        "titulos": ["" for _ in range(10)],
        "subtitulos": ["" for _ in range(10)],
        "keywords_trends": ["" for _ in range(10)],
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
        "- Si la evidencia es escasa o irrelevante para formar una estrategia coherente, DEJA LOS CAMPOS EN BLANCO (usando cadenas vacias \"\"). NO inventes informacion ni uses textos de relleno genericos.\n"
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


def clasificar_intencion_ia(keywords: list[str], keyword_base: str, pais: str) -> dict:
    """
    Clasifica un conjunto de keywords en categorías de intención, etapa del funnel
    y formato recomendado de contenido usando Groq LLM.
    """
    if not GROQ_API_KEY or not keywords:
        return {}

    muestra = keywords[:30]
    prompt = (
        f"Eres un consultor SEO senior. Clasifica estas palabras clave sobre '{keyword_base}' para {pais}.\n"
        "Devuelve UNICAMENTE un objeto JSON donde cada clave es la keyword exacta y el valor es un objeto con:\n"
        '- "intencion": "Informativa" | "Comercial" | "Transaccional" | "Navegacional"\n'
        '- "funnel": "ToFU" | "MoFU" | "BoFU"\n'
        '- "formato_recomendado": "Guia/Tutorial" | "Comparativa/Review" | "Landing/Precios" | "Video"\n\n'
        f"Keywords:\n{json.dumps(muestra, ensure_ascii=False)}"
    )

    try:
        resultado = _post_groq_json(prompt, timeout=45)
        if isinstance(resultado, dict):
            return resultado
    except Exception as e:
        logger.warning("Error en clasificar_intencion_ia: %s", e)
    return {}


def generar_clusters_tematicos(keywords: list[str], keyword_base: str) -> list[dict]:
    """
    Agrupa palabras clave en clusters semánticos (Pilares de contenido)
    para evitar canibalización y estructurar la arquitectura del sitio.
    """
    if not GROQ_API_KEY or not keywords:
        return []

    muestra = keywords[:40]
    prompt = (
        f"Eres un arquitecto de contenido SEO. Agrupa estas keywords derivadas de '{keyword_base}' "
        "en clusters semánticos coherentes (grupos de temas relacionados).\n\n"
        "Devuelve UNICAMENTE un JSON Array con este formato:\n"
        "[\n"
        "  {\n"
        '    "nombre_cluster": "Nombre temático del cluster",\n'
        '    "intencion_principal": "Informativa|Comercial|Transaccional",\n'
        '    "h1_sugerido": "Título principal recomendado para este cluster",\n'
        '    "keywords": ["kw1", "kw2", "kw3"]\n'
        "  }\n"
        "]\n\n"
        f"Keywords a agrupar:\n{json.dumps(muestra, ensure_ascii=False)}"
    )

    try:
        clusters = _post_groq_json(prompt, timeout=45)
        if isinstance(clusters, list):
            return clusters
    except Exception as e:
        logger.warning("Error en generar_clusters_tematicos: %s", e)
    return []


def generar_schema_y_meta_tags(
    keyword_base: str,
    preguntas: list[str],
    pais: str = "Colombia",
) -> dict:
    """
    Genera Meta Tags de alto CTR y código de Marcado Estructurado Schema FAQPage (JSON-LD)
    listo para copiar y pegar en WordPress, Shopify o aplicaciones web.
    """
    preguntas_muestra = [p for p in preguntas if p.strip()][:5]

    # Fallback determinista si no hay IA disponible
    slug_limpio = re.sub(r"[^a-zA-Z0-9\s-]", "", keyword_base.lower()).strip().replace(" ", "-")
    fallback = {
        "meta_title": f"{keyword_base.title()}: Guía Completa y Preguntas Frecuentes"[:60],
        "meta_titles_alternativos": [
            f"¿Qué es {keyword_base.title()}? Todo lo que debes saber"[:60],
            f"{keyword_base.title()} en {pais}: Precios, Guía y Consejos"[:60],
        ],
        "meta_description": f"Descubre todo sobre {keyword_base}: guía definitiva, respuestas a dudas frecuentes y consejos expertos para {pais}. ¡Haz clic aquí!"[:155],
        "slug_sugerido": slug_limpio,
        "og_tags": {
            "og:title": f"{keyword_base.title()}: Guía y Preguntas Frecuentes",
            "og:description": f"Todo sobre {keyword_base} con respuestas a dudas frecuentes.",
            "og:type": "article",
        },
        "faq_items": [
            {"pregunta": p, "respuesta": f"Explicación detallada y respuesta concisa sobre {p} para el usuario en {pais}."}
            for p in preguntas_muestra
        ],
        "schema_faq_json": {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": p,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"Información completa sobre {p}."
                    }
                }
                for p in preguntas_muestra
            ]
        }
    }
    fallback["schema_faq_string"] = (
        '<script type="application/ld+json">\n'
        + json.dumps(fallback["schema_faq_json"], indent=2, ensure_ascii=False)
        + "\n</script>"
    )

    if not GROQ_API_KEY:
        return fallback

    prompt = (
        f"Eres un experto en SEO On-Page y Copywriting de Alto CTR para medios digitales en {pais}.\n"
        f"A partir del término principal '{keyword_base}' y estas preguntas reales de usuarios:\n"
        f"{json.dumps(preguntas_muestra, ensure_ascii=False)}\n\n"
        "TAREA: Genera los Meta Tags optimizados para clics (CTR) y el marcado estructurado Schema FAQPage (JSON-LD).\n"
        "REGLAS:\n"
        "1. meta_title: Máximo 60 caracteres. Debe incluir la keyword principal y un gancho emocional o beneficio claro.\n"
        "2. meta_titles_alternativos: Exactamente 2 títulos alternativos (uno en formato pregunta y otro con beneficio/año).\n"
        "3. meta_description: Entre 120 y 155 caracteres con llamado a la acción (CTA) convincente.\n"
        "4. slug_sugerido: URL amigable en minúsculas separada por guiones.\n"
        "5. faq_items: Array con 3 a 5 preguntas reales y sus respuestas directas, profesionales y concisas (2 a 3 oraciones cada una).\n\n"
        "Devuelve UNICAMENTE este JSON sin texto adicional:\n"
        "{\n"
        '  "meta_title": "Título SEO <= 60 caracteres",\n'
        '  "meta_titles_alternativos": ["Título 2", "Título 3"],\n'
        '  "meta_description": "Descripción persuasiva con CTA <= 155 caracteres",\n'
        '  "slug_sugerido": "slug-url-amigable",\n'
        '  "faq_items": [\n'
        '    {"pregunta": "¿Pregunta exacta?", "respuesta": "Respuesta directa y clara."}\n'
        "  ]\n"
        "}"
    )

    try:
        data = _post_groq_json(prompt, timeout=40)
        if isinstance(data, dict) and "meta_title" in data:
            faq_items = data.get("faq_items", fallback["faq_items"])
            schema_json = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item.get("pregunta", ""),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": item.get("respuesta", "")
                        }
                    }
                    for item in faq_items if isinstance(item, dict) and item.get("pregunta")
                ]
            }
            schema_string = (
                '<script type="application/ld+json">\n'
                + json.dumps(schema_json, indent=2, ensure_ascii=False)
                + "\n</script>"
            )

            return {
                "meta_title": str(data.get("meta_title", fallback["meta_title"]))[:60],
                "meta_titles_alternativos": [str(t)[:60] for t in data.get("meta_titles_alternativos", fallback["meta_titles_alternativos"])],
                "meta_description": str(data.get("meta_description", fallback["meta_description"]))[:155],
                "slug_sugerido": str(data.get("slug_sugerido", fallback["slug_sugerido"])),
                "og_tags": {
                    "og:title": str(data.get("meta_title", fallback["meta_title"]))[:60],
                    "og:description": str(data.get("meta_description", fallback["meta_description"]))[:155],
                    "og:type": "article",
                },
                "faq_items": faq_items,
                "schema_faq_json": schema_json,
                "schema_faq_string": schema_string,
            }
    except Exception as e:
        logger.warning("Error en generar_schema_y_meta_tags: %s", e)

    return fallback


def generar_copywriting_ads_y_hooks(
    keyword_base: str,
    preguntas: list[str] = None,
    intencion: str = "Informativa / Comercial",
    pais: str = "Colombia",
) -> dict:
    """
    Genera copies de alta conversión para Google Ads (PPC), Facebook/Instagram Ads
    y ganchos (hooks) virales con guiones de 30s para TikTok / Reels / Shorts.
    """
    preguntas_muestra = [p for p in (preguntas or []) if p.strip()][:5]

    kw_cap = keyword_base.title()
    fallback = {
        "google_ads": {
            "titulos": [
                f"{kw_cap} en {pais}"[:30],
                f"Mejor {kw_cap} 2026"[:30],
                "Precios y Ofertas Hoy"[:30],
                "Guía Rápida y Fácil"[:30],
                "Cotiza 100% Online"[:30],
            ],
            "descripciones": [
                f"Descubre todo sobre {keyword_base} con asesoría experta. Calidad garantizada. ¡Entra ya!"[:90],
                f"Aprende paso a paso cómo funciona {keyword_base}. Precios claros y transparentes."[:90],
                f"¿Buscando {keyword_base}? Encuentra las mejores opciones en {pais}. ¡Haz clic aquí!"[:90],
            ]
        },
        "social_ads": {
            "hook_scroll_stopper": f"🚨 ¿Pensando en {keyword_base}? No cometas el error que el 90% hace...",
            "copy_pas": f"Sabemos lo frustrante que es buscar información clara sobre {keyword_base} y solo encontrar términos confusos.\n\nPor eso creamos esta guía completa y práctica: para que conozcas precios reales, beneficios y el paso a paso exacto.\n\n👉 Toca el enlace abajo y descúbrelo en 2 minutos.",
            "cta_boton": "Más Información"
        },
        "tiktok_reels_hooks": [
            f"El error número 1 que estás cometiendo con {keyword_base} (y cómo evitarlo hoy)",
            f"3 cosas que NADIE te dice sobre {keyword_base} antes de empezar...",
            f"Si tuviera que empezar de cero con {keyword_base}, haría exactamente esto:",
            f"Deja de perder tiempo: la forma correcta de hacer {keyword_base} en 2026",
            f"¿Vale la pena {keyword_base}? Te digo la verdad sin filtros en 30 segundos 👇",
        ],
        "guion_video_30s": {
            "segundos_0_3_gancho": f"¡Detén el scroll! Si buscas {keyword_base}, tienes que ver esto.",
            "segundos_4_15_problema": f"La mayoría de personas comete el error de no comparar opciones y termina pagando de más o perdiendo tiempo.",
            "segundos_16_25_solucion": "El truco está en seguir estos 3 pasos clave que te ahorrarán horas de investigación.",
            "segundos_26_30_cta": "Guarda este video para no olvidarlo y sígueme para más consejos como este."
        }
    }

    if not GROQ_API_KEY:
        return fallback

    prompt = (
        f"Eres un Director Creativo de Performance Marketing y Copywriter de respuesta directa en {pais}.\n"
        f"Crea una suite completa de anuncios y contenido viral para: '{keyword_base}'.\n"
        f"Intención detectada: {intencion}.\n"
        f"Dudas reales de los usuarios: {json.dumps(preguntas_muestra, ensure_ascii=False)}\n\n"
        "REGLAS ESTRICTAS DE CARACTERES:\n"
        "1. google_ads.titulos: Exactamente 5 títulos persuasivos, CADA UNO DE MÁXIMO 30 CARACTERES.\n"
        "2. google_ads.descripciones: Exactamente 3 descripciones persuasivas con CTA, CADA UNA DE MÁXIMO 90 CARACTERES.\n"
        "3. social_ads: Hook inicial de 1-2 líneas para detener el scroll + cuerpo persuasivo con fórmula PAS (Problema-Agitación-Solución).\n"
        "4. tiktok_reels_hooks: 5 ganchos virales de alta retención para los primeros 3 segundos de un video.\n"
        "5. guion_video_30s: Guion estructurado por bloques de tiempo (0-3s, 4-15s, 16-25s, 26-30s).\n\n"
        "Devuelve UNICAMENTE este JSON sin markdown adicional:\n"
        "{\n"
        '  "google_ads": {\n'
        '    "titulos": ["Título 1 <= 30 car", "Título 2 <= 30 car", "Título 3", "Título 4", "Título 5"],\n'
        '    "descripciones": ["Desc 1 <= 90 caracteres con CTA", "Desc 2 <= 90 car", "Desc 3 <= 90 car"]\n'
        "  },\n"
        '  "social_ads": {\n'
        '    "hook_scroll_stopper": "Gancho inicial impactante...",\n'
        '    "copy_pas": "Cuerpo del anuncio con fórmula PAS...",\n'
        '    "cta_boton": "Más Información | Registrarte | Comprar Ahora"\n'
        "  },\n"
        '  "tiktok_reels_hooks": [\n'
        '    "Gancho 1...", "Gancho 2...", "Gancho 3...", "Gancho 4...", "Gancho 5..."\n'
        "  ],\n"
        '  "guion_video_30s": {\n'
        '    "segundos_0_3_gancho": "Frase de apertura gancho...",\n'
        '    "segundos_4_15_problema": "Problema o mito...",\n'
        '    "segundos_16_25_solucion": "Solución o consejo...",\n'
        '    "segundos_26_30_cta": "Llamado a la acción..."\n'
        "  }\n"
        "}"
    )

    try:
        data = _post_groq_json(prompt, timeout=45)
        if isinstance(data, dict) and "google_ads" in data:
            g_ads = data.get("google_ads", {})
            titulos = [str(t)[:30] for t in g_ads.get("titulos", fallback["google_ads"]["titulos"])][:5]
            descripciones = [str(d)[:90] for d in g_ads.get("descripciones", fallback["google_ads"]["descripciones"])][:3]

            return {
                "google_ads": {
                    "titulos": titulos,
                    "descripciones": descripciones,
                },
                "social_ads": data.get("social_ads", fallback["social_ads"]),
                "tiktok_reels_hooks": [str(h) for h in data.get("tiktok_reels_hooks", fallback["tiktok_reels_hooks"])][:5],
                "guion_video_30s": data.get("guion_video_30s", fallback["guion_video_30s"]),
            }
    except Exception as e:
        logger.warning("Error en generar_copywriting_ads_y_hooks: %s", e)

    return fallback



