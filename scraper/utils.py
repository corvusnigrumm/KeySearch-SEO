"""
Utilidades compartidas para los módulos de scraping.
"""

import re
import unicodedata
from datetime import datetime


def limpiar_texto(texto: str) -> str:
    """Limpia un texto eliminando espacios extra y caracteres no deseados."""
    if not texto:
        return ""
    # Normalizar unicode (NFC compone los acentos para compatibilidad con Windows)
    texto = unicodedata.normalize("NFC", texto)
    # Eliminar espacios múltiples
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def dedupe_key(texto: str) -> str:
    """Genera una clave normalizada para deduplicar textos de Google."""
    texto = limpiar_texto(texto)
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", " ", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def slugify(texto: str) -> str:
    """Convierte un texto a un slug seguro para nombres de archivo."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", errors="ignore").decode("ascii")
    texto = re.sub(r"[^\w\s-]", "", texto).strip().lower()
    texto = re.sub(r"[-\s]+", "_", texto)
    return texto[:80]  # Limitar longitud


def generar_timestamp() -> str:
    """Genera un timestamp para nombres de archivo."""
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def generar_nombre_archivo(keyword: str, extension: str = "xlsx") -> str:
    """Genera un nombre de archivo basado en la keyword y timestamp."""
    slug = slugify(keyword)
    ts = generar_timestamp()
    return f"{slug}_{ts}.{extension}"


def es_relevante_riguroso(keyword_base: str, sugerencia: str) -> bool:
    """
    Filtro de relevancia optimizado para minería intensiva:
    Valida que la sugerencia esté semánticamente relacionada con la keyword principal.
    Permite derivaciones, plurales, sinónimos y coincidencia de palabras clave principales
    para no descartar sugerencias valiosas multi-motor.
    """
    kb = dedupe_key(keyword_base)
    sug = dedupe_key(sugerencia)

    if not kb or not sug:
        return False

    # Coincidencia exacta o contención directa (el caso más común)
    if kb in sug or sug in kb:
        return True

    palabras_kb = [p for p in kb.split() if len(p) > 1]
    if not palabras_kb:
        return kb in sug

    def _stem(word: str) -> str:
        """Genera stem simple removiendo terminaciones comunes en español."""
        if len(word) <= 3:
            return word
        # Remover terminaciones plurales y comunes
        for suffix in ("aciones", "mientos", "miento", "amiento", "imiento", "iones",
                        "nes", "res", "les", "ces", "ges", "xes", "zes", "ches",
                        "ment", "ent", "ant", "ista", "ismo", "able", "ible",
                        "oso", "osa", "oso", "esa", "ado", "ada", "ido", "ida",
                        "ar", "er", "ir", "arse", "erse", "irse",
                        "ando", "iendo", "yendo",
                        "s", "a", "o", "e", "i"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[:-len(suffix)]
        return word

    stems_kb = [_stem(p) for p in palabras_kb]

    # Para keywords de 1 a 2 palabras
    if len(palabras_kb) <= 2:
        for i, p in enumerate(palabras_kb):
            stem = stems_kb[i]
            if stem in sug or p in sug:
                return True
        return False

    # Para keywords de 3 o más palabras
    coincidencias = 0
    for i, p in enumerate(palabras_kb):
        stem = stems_kb[i]
        if stem in sug or p in sug:
            coincidencias += 1

    umbral_minimo = max(1, int(len(palabras_kb) * 0.30))
    return coincidencias >= umbral_minimo
