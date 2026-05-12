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
    Filtro riguroso: la sugerencia debe contener la palabra clave original
    (o sus palabras principales) para no traer basura como resultados 
    que solo comparten las primeras letras (ej. 'madre' -> 'madrid').
    """
    kb = dedupe_key(keyword_base)
    sug = dedupe_key(sugerencia)
    
    if not kb or not sug:
        return False
        
    # Validacion exacta de la keyword completa (el caso mas seguro)
    if kb in sug:
        return True
        
    # Manejo de plurales basicos si la keyword es una sola palabra
    palabras_kb = kb.split()
    if len(palabras_kb) == 1:
        if f"{kb}s" in sug or f"{kb}es" in sug:
            return True
        # Si termina en s, buscar singular
        if kb.endswith('s') and kb[:-1] in sug:
            return True
            
    # Para keywords compuestas, exigir que todas las palabras relevantes aparezcan
    # Ignoramos stopwords basicas de 2 letras (de, en, el, la...)
    palabras_relevantes = [p for p in palabras_kb if len(p) > 2]
    if palabras_relevantes:
        todas_presentes = all(p in sug or f"{p}s" in sug or (p.endswith('s') and p[:-1] in sug) for p in palabras_relevantes)
        if todas_presentes:
            return True

    return False
