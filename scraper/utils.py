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
