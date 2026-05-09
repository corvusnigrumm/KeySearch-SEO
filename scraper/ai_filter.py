import json
import logging
import requests

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)


def _post_groq_json(prompt: str, timeout: int = 35):
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
            {"role": "system", "content": "You are a JSON-only API. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        return json.loads(content)
    except Exception as e:
        logger.warning("Error en llamada Groq JSON: %s", e)
        return None

def filtrar_con_ia(keywords: list[str], keyword_base: str, pais: str) -> list[str]:
    """
    Usa la API de Groq para filtrar palabras clave irrelevantes o de otros paises.
    Si hay algun error o la API no responde, devuelve la lista original intacta.
    """
    if not GROQ_API_KEY or not keywords:
        return keywords

    prompt = (
        f"Actua como un analista SEO estricto. Analizas una lista de palabras clave descubiertas a partir de la keyword original: '{keyword_base}' "
        f"para el pais: '{pais}'.\n"
        f"Tu objetivo es limpiar resultados basura. Elimina CUALQUIER palabra clave que:\n"
        f"1. Tenga intencion de otro pais, ciudad o region fuera de {pais} (ej. si el pais es Colombia, elimina keywords que digan 'el salvador', 'mexico', 'lima', 'españa', etc.).\n"
        f"2. No tenga NINGUNA relacion o sentido util con '{keyword_base}'.\n\n"
        f"Responde UNICAMENTE con un JSON Array de strings conteniendo las keywords que SÍ pasaron el filtro. NO agregues texto markdown, ni explicaciones. Solo el array.\n\n"
        f"Lista original:\n"
        f"{json.dumps(keywords, ensure_ascii=False)}"
    )

    try:
        filtered_list = _post_groq_json(prompt, timeout=25)
        if isinstance(filtered_list, list):
            # Aseguramos que solo devuelva keywords que realmente existian en la original (evitar alucinaciones)
            original_set = set(keywords)
            return [kw for kw in filtered_list if kw in original_set]
            
        return keywords
    except Exception as e:
        logger.warning(f"Error en AI Filter (Groq): {e}. Se utilizara la lista original.")
        return keywords


def generar_bloques_editoriales(
    keyword_base: str,
    pais: str,
    top_autocomplete: list[str],
    top_paa: list[str],
    top_preguntas_autocomplete: list[str],
    top_relacionadas: list[str],
) -> dict:
    """
    Genera bloques editoriales para la plantilla de informe.
    Devuelve un dict con claves:
      - ejes (4 lineas)
      - propuesta (1 linea)
      - enfoque (1 linea)
      - titulos (5 lineas)
      - subtitulos (4 lineas)
    """
    fallback = {
        "ejes": [
            f"Autocompletado: {top_autocomplete[0] if top_autocomplete else keyword_base}",
            f"Preguntas PAA: {top_paa[0] if top_paa else keyword_base}",
            f"Preguntas autocompletado: {top_preguntas_autocomplete[0] if top_preguntas_autocomplete else keyword_base}",
            f"Busquedas relacionadas: {top_relacionadas[0] if top_relacionadas else keyword_base}",
        ],
        "propuesta": f"Guia completa sobre {keyword_base}",
        "enfoque": f"Resolver dudas reales de usuarios en {pais} con enfoque comparativo y accionable.",
        "titulos": [
            f"{keyword_base}: guia completa 2026",
            f"Todo sobre {keyword_base}: dudas y respuestas",
            f"{keyword_base}: comparativas y recomendaciones",
            f"{keyword_base}: errores comunes y soluciones",
            f"{keyword_base}: lo que debes saber antes de decidir",
        ],
        "subtitulos": [
            "Panorama general y contexto",
            "Comparativas clave",
            "Errores frecuentes y soluciones",
            "Checklist final para decidir",
        ],
    }

    if not GROQ_API_KEY:
        return fallback

    prompt = (
        "Actua como estratega SEO senior. Construye contenido editorial en ESPANOL para una plantilla de informe.\n"
        f"Keyword base: '{keyword_base}'. Pais objetivo: '{pais}'.\n"
        "Usa SOLO esta evidencia (Top 5 por fuente):\n"
        f"- Autocompletado: {json.dumps(top_autocomplete, ensure_ascii=False)}\n"
        f"- Preguntas PAA: {json.dumps(top_paa, ensure_ascii=False)}\n"
        f"- Preguntas Autocompletado: {json.dumps(top_preguntas_autocomplete, ensure_ascii=False)}\n"
        f"- Busquedas relacionadas: {json.dumps(top_relacionadas, ensure_ascii=False)}\n\n"
        "Devuelve UNICAMENTE un JSON con esta estructura exacta:\n"
        "{\n"
        '  "ejes": ["...", "...", "...", "..."],\n'
        '  "propuesta": "...",\n'
        '  "enfoque": "...",\n'
        '  "titulos": ["...", "...", "...", "...", "..."],\n'
        '  "subtitulos": ["...", "...", "...", "..."]\n'
        "}\n"
        "Reglas:\n"
        "- ejes: 4 lineas (una por fuente), concretas.\n"
        "- propuesta: 1 linea corta (tema central del articulo).\n"
        "- enfoque: 1 parrafo corto de intencion y angulo.\n"
        "- titulos: exactamente 5, estilo SEO, sin clickbait absurdo.\n"
        "- subtitulos: exactamente 4, alineados a los titulos.\n"
        "- No markdown, no explicaciones fuera del JSON."
    )

    result = _post_groq_json(prompt, timeout=40)
    if not isinstance(result, dict):
        return fallback

    ejes = result.get("ejes") if isinstance(result.get("ejes"), list) else []
    titulos = result.get("titulos") if isinstance(result.get("titulos"), list) else []
    subtitulos = result.get("subtitulos") if isinstance(result.get("subtitulos"), list) else []
    propuesta = result.get("propuesta") if isinstance(result.get("propuesta"), str) else ""
    enfoque = result.get("enfoque") if isinstance(result.get("enfoque"), str) else ""

    merged = {
        "ejes": [str(x).strip() for x in (ejes[:4] if ejes else fallback["ejes"])],
        "propuesta": (propuesta or fallback["propuesta"]).strip(),
        "enfoque": (enfoque or fallback["enfoque"]).strip(),
        "titulos": [str(x).strip() for x in (titulos[:5] if titulos else fallback["titulos"])],
        "subtitulos": [str(x).strip() for x in (subtitulos[:4] if subtitulos else fallback["subtitulos"])],
    }

    while len(merged["ejes"]) < 4:
        merged["ejes"].append(fallback["ejes"][len(merged["ejes"])])
    while len(merged["titulos"]) < 5:
        merged["titulos"].append(fallback["titulos"][len(merged["titulos"])])
    while len(merged["subtitulos"]) < 4:
        merged["subtitulos"].append(fallback["subtitulos"][len(merged["subtitulos"])])

    return merged
