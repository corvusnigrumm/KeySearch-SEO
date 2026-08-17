"""
Generador de contenido IA: bloques editoriales, clusters, schema FAQPage y copies de ads.
"""

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
    """Genera bloques editoriales para la plantilla de informe."""
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
    """Clasifica keywords por intencion, funnel y formato recomendado via IA."""
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
    """Agrupa keywords en clusters semanticos via IA."""
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


def generar_schema_y_meta_tags(
    keyword_base: str,
    preguntas: list[str],
    pais: str = "Colombia",
) -> dict:
    """Genera Meta Tags y Schema FAQPage JSON-LD."""
    preguntas_muestra = [p for p in preguntas if p.strip()][:5]
    slug_limpio = re.sub(r"[^a-zA-Z0-9\s-]", "", keyword_base.lower()).strip().replace(" ", "-")
    fallback = {
        "meta_title": f"{keyword_base.title()}: Guia Completa y Preguntas Frecuentes"[:60],
        "meta_titles_alternativos": [
            f"Que es {keyword_base.title()}? Todo lo que debes saber"[:60],
            f"{keyword_base.title()} en {pais}: Precios, Guia y Consejos"[:60],
        ],
        "meta_description": f"Descubre todo sobre {keyword_base}: guia definitiva, respuestas a dudas frecuentes y consejos expertos para {pais}."[
            :155
        ],
        "slug_sugerido": slug_limpio,
        "og_tags": {
            "og:title": f"{keyword_base.title()}: Guia y Preguntas Frecuentes",
            "og:description": f"Todo sobre {keyword_base} con respuestas a dudas frecuentes.",
            "og:type": "article",
        },
        "faq_items": [
            {"pregunta": p, "respuesta": f"Informacion detallada sobre {p} para el usuario en {pais}."}
            for p in preguntas_muestra
        ],
        "schema_faq_json": {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": p,
                    "acceptedAnswer": {"@type": "Answer", "text": f"Informacion completa sobre {p}."},
                }
                for p in preguntas_muestra
            ],
        },
    }
    fallback["schema_faq_string"] = (
        '<script type="application/ld+json">\n'
        + json.dumps(fallback["schema_faq_json"], indent=2, ensure_ascii=False)
        + "\n</script>"
    )

    if not GROQ_API_KEY:
        return fallback

    prompt = (
        f"Eres un experto en SEO On-Page y Copywriting de Alto CTR para {pais}.\n"
        f"Keyword: '{keyword_base}'. Preguntas: {json.dumps(preguntas_muestra, ensure_ascii=False)}\n\n"
        "Genera meta tags optimizados y Schema FAQPage.\n"
        "REGLAS: meta_title <= 60 car. meta_description entre 120-155 car con CTA.\n"
        'Devuelve: {"meta_title": "", "meta_titles_alternativos": ["", ""], '
        '"meta_description": "", "slug_sugerido": "", '
        '"faq_items": [{"pregunta": "", "respuesta": ""}]}'
    )

    try:
        data = post_groq_json(prompt, timeout=40)
        if isinstance(data, dict) and "meta_title" in data:
            faq_items = data.get("faq_items", fallback["faq_items"])
            schema_json = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item.get("pregunta", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": item.get("respuesta", "")},
                    }
                    for item in faq_items
                    if isinstance(item, dict) and item.get("pregunta")
                ],
            }
            schema_string = (
                '<script type="application/ld+json">\n'
                + json.dumps(schema_json, indent=2, ensure_ascii=False)
                + "\n</script>"
            )
            return {
                "meta_title": str(data.get("meta_title", fallback["meta_title"]))[:60],
                "meta_titles_alternativos": [
                    str(t)[:60] for t in data.get("meta_titles_alternativos", fallback["meta_titles_alternativos"])
                ],
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
    """Genera copies de Google Ads, Facebook/Instagram Ads y hooks para TikTok/Reels."""
    preguntas_muestra = [p for p in (preguntas or []) if p.strip()][:5]
    kw_cap = keyword_base.title()
    fallback = {
        "google_ads": {
            "titulos": [
                f"{kw_cap} en {pais}"[:30],
                f"Mejor {kw_cap} 2026"[:30],
                "Precios y Ofertas Hoy"[:30],
                "Guia Rapida y Facil"[:30],
                "Cotiza 100% Online"[:30],
            ],
            "descripciones": [
                f"Descubre todo sobre {keyword_base} con asesoria experta. Calidad garantizada."[:90],
                f"Aprende paso a paso como funciona {keyword_base}. Precios claros."[:90],
                f"Buscando {keyword_base}? Encuentra las mejores opciones en {pais}."[:90],
            ],
        },
        "social_ads": {
            "hook_scroll_stopper": f"Alerta: Pensando en {keyword_base}? No cometas este error...",
            "copy_pas": f"Sabemos lo frustrante que es buscar informacion clara sobre {keyword_base}.\n\nPor eso creamos esta guia completa y practica.\n\nToca el enlace y descubrelo.",
            "cta_boton": "Mas Informacion",
        },
        "tiktok_reels_hooks": [
            f"El error numero 1 con {keyword_base} (y como evitarlo hoy)",
            f"3 cosas que NADIE te dice sobre {keyword_base}",
            f"Si tuviera que empezar de cero con {keyword_base}, haria esto:",
            f"Deja de perder tiempo: la forma correcta de {keyword_base} en 2026",
            f"Vale la pena {keyword_base}? Te digo la verdad sin filtros",
        ],
        "guion_video_30s": {
            "segundos_0_3_gancho": f"Deten el scroll! Si buscas {keyword_base}, mira esto.",
            "segundos_4_15_problema": f"La mayoria comete el error de no comparar opciones con {keyword_base}.",
            "segundos_16_25_solucion": "El truco esta en seguir estos 3 pasos clave.",
            "segundos_26_30_cta": "Guarda este video y sigieme para mas consejos.",
        },
    }

    if not GROQ_API_KEY:
        return fallback

    prompt = (
        f"Eres un Director Creativo de Performance Marketing en {pais}.\n"
        f"Crea copies para: '{keyword_base}'. Intencion: {intencion}.\n"
        f"Dudas reales: {json.dumps(preguntas_muestra, ensure_ascii=False)}\n\n"
        "REGLAS: titulos <= 30 car, descripciones <= 90 car.\n"
        'Devuelve: {"google_ads": {"titulos": [...], "descripciones": [...]}, '
        '"social_ads": {"hook_scroll_stopper": "", "copy_pas": "", "cta_boton": ""}, '
        '"tiktok_reels_hooks": [...], "guion_video_30s": {"segundos_0_3_gancho": "", ...}}'
    )

    try:
        data = post_groq_json(prompt, timeout=45)
        if isinstance(data, dict) and "google_ads" in data:
            g_ads = data.get("google_ads", {})
            return {
                "google_ads": {
                    "titulos": [str(t)[:30] for t in g_ads.get("titulos", fallback["google_ads"]["titulos"])][:5],
                    "descripciones": [
                        str(d)[:90] for d in g_ads.get("descripciones", fallback["google_ads"]["descripciones"])
                    ][:3],
                },
                "social_ads": data.get("social_ads", fallback["social_ads"]),
                "tiktok_reels_hooks": [str(h) for h in data.get("tiktok_reels_hooks", fallback["tiktok_reels_hooks"])][
                    :5
                ],
                "guion_video_30s": data.get("guion_video_30s", fallback["guion_video_30s"]),
            }
    except Exception as e:
        logger.warning("Error en generar_copywriting_ads_y_hooks: %s", e)

    return fallback
