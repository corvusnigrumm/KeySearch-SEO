"""
Generador de contenido IA: bloques editoriales, clusters, schema FAQPage y copies de ads.
"""

import datetime
import json
import logging
import re

from config import GROQ_API_KEY
from scraper.ai_client import post_groq_json

logger = logging.getLogger(__name__)


def generar_bloques_editoriales(
    keyword_base: str,
    pais: str,
    top_autocomplete: list[str],
    top_paa: list[str],
    top_preguntas_autocomplete: list[str],
    top_relacionadas: list[str],
    top_keywords_trends: list[str] = None,
) -> dict:
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
    prompt = (
        "Eres un estratega SEO senior con 10 anos de experiencia en medios digitales hispanohablantes. "
        "Tu tarea es generar bloques editoriales ESTRATEGICOS Y PROFUNDOS para una plantilla de informe SEO "
        "que usaran redactores profesionales para planificar su contenido.\n\n"
        f"KEYWORD PRINCIPAL: '{keyword_base}'\n"
        f"PAIS OBJETIVO: '{pais}'\n\n"
        "EVIDENCIA REAL DE GOOGLE:\n"
        f"- Autocompletado (Top 15): {json.dumps(top_autocomplete[:15], ensure_ascii=False)}\n"
        f"- Preguntas PAA (Top 15): {json.dumps(top_paa[:15], ensure_ascii=False)}\n"
        f"- Preguntas por Autocompletado (Top 15): {json.dumps(top_preguntas_autocomplete[:15], ensure_ascii=False)}\n"
        f"- Busquedas relacionadas (Top 15): {json.dumps(top_relacionadas[:15], ensure_ascii=False)}\n"
        f"- Keywords con mayor volumen/tendencia (Top 20): {json.dumps(top_keywords_trends[:20], ensure_ascii=False)}\n\n"
        "Devuelve UNICAMENTE este JSON:\n"
        "{\n"
        '  "intencion_predominante": "informacional|transaccional|navegacional|comparativa",\n'
        '  "ejes": ["9 ejes tematicos"],\n'
        '  "propuesta": "1 linea",\n'
        '  "enfoque": "2-3 oraciones",\n'
        '  "titulos": ["10 titulos H1"],\n'
        '  "subtitulos": ["10 subtitulos H2/H3"],\n'
        '  "keywords_trends": ["10 keywords long-tail"]\n'
        "}"
    )
    result = post_groq_json(prompt, timeout=55)
    if not isinstance(result, dict):
        return fallback
    ejes = result.get("ejes") if isinstance(result.get("ejes"), list) else []
    titulos = result.get("titulos") if isinstance(result.get("titulos"), list) else []
    subtitulos = result.get("subtitulos") if isinstance(result.get("subtitulos"), list) else []
    kw_trends_res = result.get("keywords_trends") if isinstance(result.get("keywords_trends"), list) else []
    merged = {
        "ejes": [str(x).strip() for x in (ejes[:9] if ejes else fallback["ejes"])],
        "propuesta": str(result.get("propuesta", "") or "").strip(),
        "enfoque": str(result.get("enfoque", "") or "").strip(),
        "titulos": [str(x).strip() for x in (titulos[:10] if titulos else fallback["titulos"])],
        "subtitulos": [str(x).strip() for x in (subtitulos[:10] if subtitulos else fallback["subtitulos"])],
        "keywords_trends": [
            str(x).strip() for x in (kw_trends_res[:10] if kw_trends_res else fallback["keywords_trends"])
        ],
    }
    for key, size in [("ejes", 9), ("titulos", 10), ("subtitulos", 10), ("keywords_trends", 10)]:
        while len(merged[key]) < size:
            merged[key].append(fallback[key][len(merged[key])])
    return merged


def clasificar_intencion_ia(keywords: list[str], keyword_base: str, pais: str) -> dict:
    if not GROQ_API_KEY or not keywords:
        return {}
    prompt = (
        f"Eres un consultor SEO senior. Clasifica estas palabras clave sobre '{keyword_base}' para {pais}.\n"
        "Devuelve UNICAMENTE un objeto JSON donde cada clave es la keyword exacta y el valor es un objeto con:\n"
        '- "intencion": "Informativa" | "Comercial" | "Transaccional" | "Navegacional"\n'
        '- "funnel": "ToFU" | "MoFU" | "BoFU"\n'
        '- "formato_recomendado": "Guia/Tutorial" | "Comparativa/Review" | "Landing/Precios" | "Video"\n\n'
        f"Keywords:\n{json.dumps(keywords[:30], ensure_ascii=False)}"
    )
    try:
        resultado = post_groq_json(prompt, timeout=45)
        if isinstance(resultado, dict):
            return resultado
    except Exception as e:
        logger.warning("Error en clasificar_intencion_ia: %s", e)
    return {}


def generar_clusters_tematicos(keywords: list[str], keyword_base: str) -> list[dict]:
    if not GROQ_API_KEY or not keywords:
        return []
    prompt = (
        f"Eres un arquitecto de contenido SEO. Agrupa estas keywords derivadas de '{keyword_base}' "
        "en clusters semanticos coherentes.\n\n"
        "Devuelve UNICAMENTE un JSON Array:\n"
        '[{"nombre_cluster": "Nombre", "intencion_principal": "Informativa|Comercial|Transaccional", '
        '"h1_sugerido": "Titulo sugerido", "keywords": ["kw1", "kw2"]}]\n\n'
        f"Keywords:\n{json.dumps(keywords[:40], ensure_ascii=False)}"
    )
    try:
        clusters = post_groq_json(prompt, timeout=45)
        if isinstance(clusters, list):
            return clusters
    except Exception as e:
        logger.warning("Error en generar_clusters_tematicos: %s", e)
    return []


def _serialize_schema(schema_json: dict) -> str:
    if not schema_json:
        return ""
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(schema_json, indent=2, ensure_ascii=False)
        + "\n</script>"
    )


def _build_schema_strings(data: dict) -> None:
    parts = []
    if data.get("schema_faq_json"):
        data["schema_faq_string"] = _serialize_schema(data["schema_faq_json"])
        parts.append(data["schema_faq_string"])
    if data.get("schema_article_json"):
        parts.append(_serialize_schema(data["schema_article_json"]))
    if data.get("schema_breadcrumb_json"):
        parts.append(_serialize_schema(data["schema_breadcrumb_json"]))
    data["schema_all_string"] = "\n\n".join(parts)

def _detectar_tipo_esquema(intencion: str, keyword: str, top_keywords: list) -> list[str]:
    keyword_lower = keyword.lower()
    top_text = " ".join(top_keywords[:15]).lower()
    es_pregunta = "?" in keyword or any(keyword_lower.startswith(w) for w in ["como", "que", "cuando", "donde", "por que", "cuales", "cuanto", "quien"])
    tiene_preguntas_en_top = any("?" in k or k.lower().startswith(("como ", "que ", "cuando ", "donde ", "por que ")) for k in top_keywords[:10])
    tipos = ["Article"]
    if es_pregunta or tiene_preguntas_en_top:
        tipos.insert(0, "FAQPage")
    if any(w in keyword_lower for w in ["tutorial", "como hacer", "guia", "paso a paso", "instrucciones", "metodo", "tecnica"]):
        tipos.insert(0, "HowTo")
    if any(w in keyword_lower for w in ["receta", "ingredientes", "preparar"]):
        tipos.insert(0, "Recipe")
    if intencion and intencion.lower() in ["transaccional", "comercial"]:
        tipos.append("Product")
    tipos.append("BreadcrumbList")
    return tipos[:4]


def _generar_schema_faq(contexto: str, keyword: str, pais: str, data: dict) -> None:
    if not GROQ_API_KEY:
        data["schema_faq_json"] = None
        return
    prompt = (
        f"Eres un experto en Schema.org. Genera un FAQPage schema JSON-LD para '{keyword}' en {pais}.\n\n"
        f"CONTEXTO CLAVE:\n{contexto}\n\n"
        "Reglas: 3-5 preguntas/respuestas exactas del dominio, respuestas de 1-3 oraciones, "
        "RESPUESTAS CORTAS Y DIRECTAS, NO listas HTML.\n\n"
        "Devuelve SOLO JSON: {\"@context\": \"https://schema.org\", \"@type\": \"FAQPage\", \"mainEntity\": [...]}"
    )
    try:
        resultado = post_groq_json(prompt, timeout=45)
        if isinstance(resultado, dict) and resultado.get("@type") == "FAQPage":
            data["schema_faq_json"] = resultado
        else:
            data["schema_faq_json"] = None
    except Exception as e:
        logger.warning("Error generando FAQ schema: %s", e)
        data["schema_faq_json"] = None


def _generar_schema_article(contexto: str, keyword: str, pais: str, data: dict, intencion: str) -> None:
    if not GROQ_API_KEY:
        data["schema_article_json"] = None
        return
    hoy = datetime.date.today().isoformat()
    prompt = (
        f"Eres un experto en Schema.org. Genera un Article schema JSON-LD para '{keyword}' en {pais}.\n\n"
        f"CONTEXTO:\n{contexto}\n\n"
        f"INTENCION: {intencion}\n"
        "Genera headline, description (155 chars), datePublished, dateModified, author, publisher, mainEntityOfPage.\n"
        "Devuelve SOLO JSON: {\"@context\": \"https://schema.org\", \"@type\": \"Article\", ...}"
    )
    try:
        resultado = post_groq_json(prompt, timeout=30)
        if isinstance(resultado, dict) and resultado.get("@type") == "Article":
            if "datePublished" not in resultado:
                resultado["datePublished"] = hoy
            if "dateModified" not in resultado:
                resultado["dateModified"] = hoy
            data["schema_article_json"] = resultado
        else:
            data["schema_article_json"] = None
    except Exception as e:
        logger.warning("Error generando Article schema: %s", e)
        data["schema_article_json"] = None


def _generar_schema_breadcrumb(keyword: str, data: dict) -> None:
    base = keyword.title()
    data["schema_breadcrumb_json"] = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": "/"},
            {"@type": "ListItem", "position": 2, "name": base, "item": f"/{base.lower().replace(' ', '-')}"}
        ]
    }


def _generar_meta_tags(contexto: str, keyword: str, pais: str, data: dict, intencion: str) -> None:
    if not GROQ_API_KEY:
        data["meta_title"] = f"{keyword.title()} - Guia completa {pais}"
        data["meta_description"] = f"Descubre todo sobre {keyword} en {pais}. Informacion completa y actualizada."
        data["slug"] = keyword.lower().replace(" ", "-").replace("?", "")
        return
    prompt = (
        f"Genera meta tags SEO optimizados para '{keyword}' en {pais}.\n\n"
        f"CONTEXTO:\n{contexto}\n\n"
        f"INTENCION: {intencion}\n"
        "Devuelve JSON: {\"title\": \"max 60 chars\", \"description\": \"max 155 chars\", \"slug\": \"url-friendly\"}"
    )
    try:
        resultado = post_groq_json(prompt, timeout=20)
        if isinstance(resultado, dict):
            data["meta_title"] = str(resultado.get("title", ""))[:60] or f"{keyword.title()} - Guia completa {pais}"
            data["meta_description"] = str(resultado.get("description", ""))[:155] or f"Descubre todo sobre {keyword}."
            data["slug"] = str(resultado.get("slug", keyword.lower().replace(" ", "-")))
        else:
            data["meta_title"] = f"{keyword.title()} - Guia completa {pais}"
            data["meta_description"] = f"Descubre todo sobre {keyword} en {pais}. Informacion completa y actualizada."
            data["slug"] = keyword.lower().replace(" ", "-").replace("?", "")
    except Exception as e:
        logger.warning("Error generando meta tags: %s", e)
        data["meta_title"] = f"{keyword.title()} - Guia completa {pais}"
        data["meta_description"] = f"Descubre todo sobre {keyword} en {pais}. Informacion completa y actualizada."
        data["slug"] = keyword.lower().replace(" ", "-").replace("?", "")


def generar_schema_y_meta_tags(
    keyword: str,
    pais: str,
    top_keywords: list[str] = None,
    intencion: str = None,
    serp_analysis: dict = None,
) -> dict:
    top_keywords = top_keywords or []
    data: dict = {
        "schema_faq_json": None,
        "schema_article_json": None,
        "schema_breadcrumb_json": None,
        "meta_title": None,
        "meta_description": None,
        "slug": None,
        "schema_all_string": "",
    }

    if not keyword:
        return data

    top_kw_text = ", ".join(top_keywords[:12]) if top_keywords else "sin datos"
    serp_context = ""
    if serp_analysis:
        tops = serp_analysis.get("top_5_results", [])[:3]
        if tops:
            serp_context = "Sitios top en SERP:\n" + "\n".join(f"- {r.get('title','')} ({r.get('url','')})" for r in tops)

    contexto = f"Keyword: {keyword}\nPais: {pais}\nKeywords top: {top_kw_text}\n{serp_context}"
    tipos = _detectar_tipo_esquema(intencion or "", keyword, top_keywords)

    if "FAQPage" in tipos:
        _generar_schema_faq(contexto, keyword, pais, data)
    else:
        data["schema_faq_json"] = None

    if "Article" in tipos:
        _generar_schema_article(contexto, keyword, pais, data, intencion or "")
    else:
        data["schema_article_json"] = None

    _generar_schema_breadcrumb(keyword, data)
    _generar_meta_tags(contexto, keyword, pais, data, intencion or "")
    _build_schema_strings(data)

    return data


def _construir_contexto_serp(serp_analysis: dict, trending_keywords: list[str], sugerencias: list[str], keyword: str) -> str:
    partes = []
    if serp_analysis:
        top_5 = serp_analysis.get("top_5_results", [])[:3]
        if top_5:
            partes.append("TITULOS Y URLs TOP EN SERP:")
            for r in top_5:
                partes.append(f"- {r.get('title','')} | {r.get('url','')}")
        featured = serp_analysis.get("featured_snippets") or []
        if featured:
            partes.append("FRAGMENTS DESTACADOS: " + "; ".join(featured[:2]))
    if trending_keywords:
        partes.append("KEYWORDS TRENDING: " + ", ".join(trending_keywords[:12]))
    if sugerencias:
        partes.append("AUTOCOMPLETADO: " + ", ".join(sugerencias[:10]))
    if not partes:
        partes.append(f"Keyword base: {keyword}")
    return "\n".join(partes)


def _detectar_tipo_copy(intencion: str, keyword: str) -> str:
    kw = keyword.lower()
    if intencion in ("transaccional", "comercial") or any(w in kw for w in ["comprar", "precio", "barato", "oferta", "descuento"]):
        return "transaccional"
    if any(w in kw for w in ["tutorial", "como", "guia", "paso a paso", "ejemplo"]):
        return "educativo"
    if any(w in kw for w in ["mejor", "comparar", "vs", "review", "opinion"]):
        return "comparativo"
    return "informativo"


def _generar_copies_por_tipo(tipo: str, keyword: str, pais: str, contexto_serp: str, data: dict) -> None:
    if not GROQ_API_KEY:
        return
    prompts = {
        "transaccional": (
            f"Eres un copywriter performance de conversiones. Crea copies para '{keyword}' ({pais}).\n"
            f"CONTEXTO SERP:\n{contexto_serp}\n\n"
            "Genera: 6 HOOKS (3-8 palabras), 5 ANUNCIOS (90 chars), 5 DESCRIPCIONES (70 chars).\n"
            "Enfoque: URGENCIA + BENEFICIO CONCRETO + CTA.\n"
            "Devuelve JSON con keys: hooks[], ads_headline[], ads_description[], cta_sugerido, propuesta_valor"
        ),
        "educativo": (
            f"Eres un copywriter de contenido educativo. Crea copies para '{keyword}' ({pais}).\n"
            f"CONTEXTO SERP:\n{contexto_serp}\n\n"
            "Genera: 6 HOOKS, 5 ANUNCIOS, 5 DESCRIPCIONES.\n"
            "Enfoque: CURIOSIDAD + AUTORIDAD + SOLUCION CLARA.\n"
            "Devuelve JSON con keys: hooks[], ads_headline[], ads_description[], cta_sugerido, propuesta_valor"
        ),
        "comparativo": (
            f"Eres un copywriter de reviews y comparativas. Crea copies para '{keyword}' ({pais}).\n"
            f"CONTEXTO SERP:\n{contexto_serp}\n\n"
            "Genera: 6 HOOKS, 5 ANUNCIOS, 5 DESCRIPCIONES.\n"
            "Enfoque: DIFERENCIACION + VERIFICACION + PRUEBA SOCIAL.\n"
            "Devuelve JSON con keys: hooks[], ads_headline[], ads_description[], cta_sugerido, propuesta_valor"
        ),
    }
    prompt = prompts.get(tipo, prompts["transaccional"])
    resultado = post_groq_json(prompt, timeout=40)
    if not isinstance(resultado, dict):
        data["ad_hooks"] = [keyword] * 6
        data["ads_headline"] = [keyword] * 5
        data["ads_description"] = [f"Conoce mas sobre {keyword}"] * 5
        data["cta_sugerido"] = "Descubre mas"
        data["propuesta_valor"] = keyword
        return
    data["ad_hooks"] = [str(x) for x in (resultado.get("hooks") or [])][:6]
    data["ads_headline"] = [str(x) for x in (resultado.get("ads_headline") or [])][:5]
    data["ads_description"] = [str(x) for x in (resultado.get("ads_description") or [])][:5]
    data["cta_sugerido"] = str(resultado.get("cta_sugerido", "Descubre mas"))
    data["propuesta_valor"] = str(resultado.get("propuesta_valor", keyword))


def _llenar_fallbacks(data: dict, keyword: str, total_h=6, total_a=5, total_d=5) -> None:
    hooks_f = [
        f"{keyword.title()} - Lo que nadie te dice",
        f"Descubre {keyword} en 5 minutos",
        f"La guia definitiva de {keyword}",
        f"{keyword.title()}: Error #1 que debes evitar",
        f"Todo sobre {keyword} de forma simple",
        f"{keyword.title()} - Resultados reales",
    ]
    ads_f = [
        f"{keyword.title()} | Guia completa",
        f"Conoce todo sobre {keyword}",
        f"{keyword.title()} - Paso a paso",
        f"Aprende {keyword} hoy",
        f"{keyword.title()} - Ejemplos reales",
    ]
    desc_f = [
        f"Aprende todo sobre {keyword} con esta guia completa y actualizada.",
        f"Guia practica de {keyword} con ejemplos y pasos claros.",
        f"Descubre como aplicar {keyword} en tu proyecto.",
        f"{keyword.title()} explicado de forma sencilla y directa.",
        f"Todo lo que necesitas saber sobre {keyword} en un solo lugar.",
    ]
    while len(data["ad_hooks"]) < total_h:
        data["ad_hooks"].append(hooks_f[len(data["ad_hooks"]) % len(hooks_f)])
    while len(data["ads_headline"]) < total_a:
        data["ads_headline"].append(ads_f[len(data["ads_headline"]) % len(ads_f)])
    while len(data["ads_description"]) < total_d:
        data["ads_description"].append(desc_f[len(data["ads_description"]) % len(desc_f)])
    if not data.get("cta_sugerido"):
        data["cta_sugerido"] = "Descubre mas"
    if not data.get("propuesta_valor"):
        data["propuesta_valor"] = keyword


def generar_copywriting_ads_y_hooks(
    keyword: str,
    pais: str,
    intencion: str = None,
    sugerencias: list[str] = None,
    serp_analysis: dict = None,
    trending_keywords: list[str] = None,
    kgr_data: dict = None,
) -> dict:
    sugerencias = sugerencias or []
    trending_keywords = trending_keywords or []
    data: dict = {
        "ad_hooks": [],
        "ads_headline": [],
        "ads_description": [],
        "cta_sugerido": "",
        "propuesta_valor": "",
    }
    if not keyword:
        data["ad_hooks"] = [""] * 6
        data["ads_headline"] = [""] * 5
        data["ads_description"] = [""] * 5
        return data

    contexto_serp = _construir_contexto_serp(serp_analysis, trending_keywords, sugerencias, keyword)
    tipo = _detectar_tipo_copy(intencion or "", keyword)

    if GROQ_API_KEY:
        _generar_copies_por_tipo(tipo, keyword, pais, contexto_serp, data)
    else:
        data["ad_hooks"] = [keyword] * 6
        data["ads_headline"] = [keyword] * 5
        data["ads_description"] = [f"Conoce mas sobre {keyword}"] * 5
        data["cta_sugerido"] = "Descubre mas"
        data["propuesta_valor"] = keyword

    _llenar_fallbacks(data, keyword)
    return data
