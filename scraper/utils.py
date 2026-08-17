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
        
    palabras_kb = [p for p in kb.split() if len(p) > 2]
    if not palabras_kb:
        # Si la keyword eran sólo conectores cortos, aceptamos si la sugerencia empieza o contiene la keyword
        return kb in sug

    # Para keywords de 1 a 2 palabras
    if len(palabras_kb) <= 2:
        # Al menos una palabra principal debe estar presente o ser raíz
        for p in palabras_kb:
            stem = p[:-1] if (len(p) > 3 and p.endswith(('s', 'a', 'o', 'e'))) else p
            if stem in sug:
                return True
        return False

    # Para keywords de 3 o más palabras (ej. "tarjetas de credito bancolombia")
    # Exigimos que al menos el 50% de las palabras clave principales coincidan
    coincidencias = 0
    for p in palabras_kb:
        stem = p[:-1] if (len(p) > 3 and p.endswith(('s', 'a', 'o', 'e'))) else p
        if stem in sug:
            coincidencias += 1

    umbral_minimo = max(1, int(len(palabras_kb) * 0.45))
    return coincidencias >= umbral_minimo
