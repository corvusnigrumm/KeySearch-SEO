"""
Módulo Generador de Content Brief Editorial y Estructura de Encabezados (H2/H3).

Genera una guía de redacción profesional (Content Brief) para redactores y copywriters:
1. Longitud sugerida de palabras (Word Count Target)
2. Estructura recomendada de encabezados H1 -> H2 -> H3
3. Preguntas frecuentes obligatorias a responder
4. Términos y entidades semánticas secundarias
5. Formato editorial sugerido (Guía, Comparativa, Tutorial)
"""

import json
import logging

from config import GROQ_API_KEY
from scraper.ai_client import post_groq_json as _post_groq_json

logger = logging.getLogger(__name__)


def generar_content_brief(
    keyword_base: str,
    sugerencias: list[str] = None,
    preguntas_paa: list[str] = None,
    preguntas_ac: list[str] = None,
    pais: str = "Colombia",
    intencion: str = "Informativa",
) -> dict:
    """
    Genera un Content Brief completo listo para entregar a un redactor de contenidos.
    """
    sugs = (sugerencias or [])[:12]
    paas = (preguntas_paa or [])[:8]
    p_acs = (preguntas_ac or [])[:8]
    todas_preguntas = list(dict.fromkeys(paas + p_acs))[:10]

    # Determinación heurística de word count y formato
    es_transaccional = "transaccional" in intencion.lower()
    es_comercial = "comercial" in intencion.lower()

    if es_transaccional:
        palabras_target = "1,000 - 1,400 palabras"
        formato_sugerido = "Landing Page / Guía de Compra y Precios"
    elif es_comercial:
        palabras_target = "1,400 - 1,800 palabras"
        formato_sugerido = "Comparativa / Review y Tabla de Mejores Opciones"
    else:
        palabras_target = "1,500 - 2,200 palabras"
        formato_sugerido = "Guía Definitiva / Artículo Pilar de Autoridad"

    fallback = {
        "keyword_principal": keyword_base,
        "pais_objetivo": pais,
        "longitud_recomendada_palabras": palabras_target,
        "formato_sugerido": formato_sugerido,
        "intencion_predominante": intencion,
        "meta_h1": f"{keyword_base.title()}: Guía Completa y Preguntas Frecuentes",
        "secciones_h2": [
            {
                "h2": f"¿Qué es {keyword_base.title()} y cómo funciona?",
                "h3_subsecciones": ["Conceptos clave esenciales", "Principales características"],
                "puntos_clave": "Definir con claridad en el primer párrafo para ganar fragmento destacado.",
            },
            {
                "h2": f"Principales beneficios de {keyword_base}",
                "h3_subsecciones": ["Ventajas más destacadas", "A quién va dirigido"],
                "puntos_clave": "Explicar beneficios tangibles con ejemplos reales.",
            },
            {
                "h2": f"Paso a paso: Cómo implementar o usar {keyword_base}",
                "h3_subsecciones": ["Requisitos previos", "Guía paso a paso"],
                "puntos_clave": "Formato lista ordenada con instrucciones claras y accionables.",
            },
            {
                "h2": "Preguntas frecuentes sobre " + keyword_base.title(),
                "h3_subsecciones": todas_preguntas[:4] if todas_preguntas else [f"Dudas comunes sobre {keyword_base}"],
                "puntos_clave": "Respuestas directas de 2 a 3 oraciones por cada pregunta.",
            },
        ],
        "terminos_semanticos_obligatorios": sugs[:8] if sugs else [keyword_base, f"consejos {keyword_base}"],
        "preguntas_obligatorias_responder": todas_preguntas[:6],
        "checklist_redactor": [
            "Incluir la keyword principal en el H1, en las primeras 100 palabras y en al menos un H2.",
            "Responder de forma directa y concisa las preguntas PAA para aspirar a Google Featured Snippets.",
            "Usar párrafos cortos (máximo 3-4 líneas) y listas con viñetas para maximizar la legibilidad.",
            "Incluir al menos 2 enlaces internos a contenidos relacionados.",
        ],
    }

    if not GROQ_API_KEY:
        return fallback

    prompt = (
        f"Eres el Editor Jefe y Estratega SEO de un medio digital en {pais}.\n"
        f"Genera un CONTENT BRIEF / GUÍA DE REDACCIÓN SEO exhaustivo para escribir el mejor artículo de internet sobre: '{keyword_base}'.\n"
        f"Intención del usuario: {intencion}.\n"
        f"Evidencia real de búsqueda (Sugerencias): {json.dumps(sugs, ensure_ascii=False)}\n"
        f"Preguntas reales de la SERP (PAA): {json.dumps(todas_preguntas, ensure_ascii=False)}\n\n"
        "REGLAS:\n"
        "1. meta_h1: Título H1 principal con alto CTR y enfoque profesional.\n"
        "2. secciones_h2: Array de 4 a 6 encabezados H2 estructurados lógicamente, cada uno con sus H3 y puntos clave a cubrir.\n"
        "3. terminos_semanticos_obligatorios: Lista de 6 a 10 términos y variaciones long-tail extraídos de la evidencia.\n"
        "4. preguntas_obligatorias_responder: 4 a 6 preguntas cruciales que el redactor debe contestar obligatoriamente.\n"
        "5. checklist_redactor: 4 consejos accionables de On-Page SEO.\n\n"
        "Devuelve UNICAMENTE un objeto JSON válido con esta estructura (sin texto extra):\n"
        "{\n"
        '  "meta_h1": "Título H1 Principal",\n'
        '  "longitud_recomendada_palabras": "1,500 - 2,000 palabras",\n'
        '  "formato_sugerido": "Guía Pilar / Comparativa",\n'
        '  "secciones_h2": [\n'
        "    {\n"
        '      "h2": "Encabezado H2",\n'
        '      "h3_subsecciones": ["Subsección H3 A", "Subsección H3 B"],\n'
        '      "puntos_clave": "Qué debe explicar el redactor en esta sección..."\n'
        "    }\n"
        "  ],\n"
        '  "terminos_semanticos_obligatorios": ["termino 1", "termino 2"],\n'
        '  "preguntas_obligatorias_responder": ["pregunta 1", "pregunta 2"],\n'
        '  "checklist_redactor": ["Punto 1", "Punto 2", "Punto 3"]\n'
        "}"
    )

    try:
        data = _post_groq_json(prompt, timeout=45)
        if isinstance(data, dict) and "meta_h1" in data:
            return {
                "keyword_principal": keyword_base,
                "pais_objetivo": pais,
                "longitud_recomendada_palabras": data.get(
                    "longitud_recomendada_palabras", fallback["longitud_recomendada_palabras"]
                ),
                "formato_sugerido": data.get("formato_sugerido", fallback["formato_sugerido"]),
                "intencion_predominante": intencion,
                "meta_h1": data.get("meta_h1", fallback["meta_h1"]),
                "secciones_h2": data.get("secciones_h2", fallback["secciones_h2"]),
                "terminos_semanticos_obligatorios": data.get(
                    "terminos_semanticos_obligatorios", fallback["terminos_semanticos_obligatorios"]
                ),
                "preguntas_obligatorias_responder": data.get(
                    "preguntas_obligatorias_responder", fallback["preguntas_obligatorias_responder"]
                ),
                "checklist_redactor": data.get("checklist_redactor", fallback["checklist_redactor"]),
            }
    except Exception as e:
        logger.warning("Error en generar_content_brief: %s", e)

    return fallback


def exportar_content_brief_markdown(brief_data: dict) -> str:
    """Convierte el Content Brief en formato Markdown listo para copiar o descargar."""
    kw = brief_data.get("keyword_principal", "")
    pais = brief_data.get("pais_objetivo", "")
    h1 = brief_data.get("meta_h1", "")
    palabras = brief_data.get("longitud_recomendada_palabras", "")
    formato = brief_data.get("formato_sugerido", "")

    md = []
    md.append(f"# 📋 Content Brief SEO: {h1}")
    md.append(f"**Palabra Clave Principal:** `{kw}` | **País Objetivo:** {pais}")
    md.append(f"**Longitud Sugerida:** {palabras} | **Formato:** {formato}\n")
    md.append("---")
    md.append("## 📐 Estructura de Encabezados (H2 / H3 Recomendados)")

    for sec in brief_data.get("secciones_h2", []):
        md.append(f"\n### {sec.get('h2')}")
        if sec.get("puntos_clave"):
            md.append(f"> 💡 **Objetivo:** {sec.get('puntos_clave')}")
        for h3 in sec.get("h3_subsecciones", []):
            md.append(f"- **H3:** {h3}")

    md.append("\n---")
    md.append("## 🔑 Términos Semánticos Secundarios (Obligatorios)")
    for term in brief_data.get("terminos_semanticos_obligatorios", []):
        md.append(f"- [ ] `{term}`")

    md.append("\n---")
    md.append("## ❓ Preguntas Frecuentes que Deben Responderse")
    for q in brief_data.get("preguntas_obligatorias_responder", []):
        md.append(f"- **{q}**")

    md.append("\n---")
    md.append("## ✅ Checklist SEO On-Page para el Redactor")
    for check in brief_data.get("checklist_redactor", []):
        md.append(f"- [ ] {check}")

    return "\n".join(md)
