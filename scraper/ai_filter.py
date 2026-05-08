import json
import logging
import requests

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

def filtrar_con_ia(keywords: list[str], keyword_base: str, pais: str) -> list[str]:
    """
    Usa la API de Groq para filtrar palabras clave irrelevantes o de otros paises.
    Si hay algun error o la API no responde, devuelve la lista original intacta.
    """
    if not GROQ_API_KEY or not keywords:
        return keywords

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    # Dividir en lotes si son demasiadas para que el LLM no se sature.
    # En este proyecto rara vez pasan de 200, lo enviamos todo.
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

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a JSON-only API. Only output a valid JSON array of strings, nothing else."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Parsear posible markdown code blocks
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        filtered_list = json.loads(content)
        
        if isinstance(filtered_list, list):
            # Aseguramos que solo devuelva keywords que realmente existian en la original (evitar alucinaciones)
            original_set = set(keywords)
            return [kw for kw in filtered_list if kw in original_set]
            
        return keywords
    except Exception as e:
        logger.warning(f"Error en AI Filter (Groq): {e}. Se utilizara la lista original.")
        return keywords
