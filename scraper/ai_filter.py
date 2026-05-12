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
        f"Actua como un analista SEO ESTRICTO E INFLEXIBLE. Analizas una lista de palabras clave descubiertas a partir de la keyword original: '{keyword_base}' "
        f"para el pais: '{pais}'.\n"
        f"Tu objetivo es limpiar resultados basura y filtraciones geograficas. Elimina CUALQUIER palabra clave que:\n"
        f"1. Tenga intencion de OTRO pais, ciudad, municipio, provincia o region que NO SEA de {pais}. Si la busqueda dice 'mexico', 'venezuela', 'argentina', 'peru', 'chile', 'españa', o ciudades de esos paises (y {pais} es otro), ELIMINALA INMEDIATAMENTE sin excepcion.\n"
        f"2. No tenga NINGUNA relacion, sentido util o coherencia con '{keyword_base}'.\n\n"
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
    top_keywords_trends: list[str] = None,
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

    prompt = (
        "Actua como estratega SEO senior. Construye contenido editorial en ESPANOL para una plantilla de informe.\n"
        f"Keyword base: '{keyword_base}'. Pais objetivo: '{pais}'.\n"
        "Usa SOLO esta evidencia (Top 5/10 por fuente):\n"
        f"- Autocompletado: {json.dumps(top_autocomplete, ensure_ascii=False)}\n"
        f"- Preguntas PAA: {json.dumps(top_paa, ensure_ascii=False)}\n"
        f"- Preguntas Autocompletado: {json.dumps(top_preguntas_autocomplete, ensure_ascii=False)}\n"
        f"- Busquedas relacionadas: {json.dumps(top_relacionadas, ensure_ascii=False)}\n"
        f"- Keywords con buen volumen/trends: {json.dumps(top_keywords_trends[:15] if top_keywords_trends else [], ensure_ascii=False)}\n\n"
        "Devuelve UNICAMENTE un JSON con esta estructura exacta:\n"
        "{\n"
        '  "ejes": ["9 ejes estrategicos aqui..."],\n'
        '  "propuesta": "...",\n'
        '  "enfoque": "...",\n'
        '  "titulos": ["10 titulos SEO aqui..."],\n'
        '  "subtitulos": ["10 subtitulos SEO aqui..."],\n'
        '  "keywords_trends": ["10 mejores keywords basadas en tendencias aqui..."]\n'
        "}\n"
        "Reglas:\n"
        "- ejes: EXACTAMENTE 9 lineas concretas (4 basadas en las fuentes y 5 adicionales estrategicas).\n"
        "- propuesta: 1 linea corta (tema central del articulo).\n"
        "- enfoque: 1 parrafo corto de intencion y angulo.\n"
        "- titulos: EXACTAMENTE 10 titulos, optimizados para SEO, con alto potencial.\n"
        "- subtitulos: EXACTAMENTE 10 subtitulos, alineados a los titulos y tematicas clave.\n"
        "- keywords_trends: EXACTAMENTE 10 keywords destacadas (utiliza las Keywords con buen volumen dadas en la evidencia).\n"
        "- No markdown, no explicaciones fuera del JSON."
    )

    result = _post_groq_json(prompt, timeout=40)
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
