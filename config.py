"""
Configuracion centralizada para la herramienta de busqueda de tendencias.

El proyecto puede trabajar con:
1. Senales HTTP de Google
2. Google Trends via pytrends
3. Google Ads API para metricas historicas reales, si esta configurada
"""
import os
import sys


def _runtime_base_dir() -> str:
    """
    Devuelve la carpeta real de trabajo de la aplicacion.

    En desarrollo usa la carpeta del proyecto.
    En un ejecutable PyInstaller usa la carpeta donde vive el .exe.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _runtime_base_dir()


def _read_optional_value(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as file_handle:
        return file_handle.read().strip()


# Idioma y pais
LANG = "es"
COUNTRY = "co"

COUNTRY_CATALOG = {
    "co": {"name": "Colombia", "google_ads_geo_targets": ["Colombia"]},
    "mx": {"name": "Mexico", "google_ads_geo_targets": ["Mexico"]},
    "es": {"name": "Espana", "google_ads_geo_targets": ["Spain"]},
    "ar": {"name": "Argentina", "google_ads_geo_targets": ["Argentina"]},
    "cl": {"name": "Chile", "google_ads_geo_targets": ["Chile"]},
    "pe": {"name": "Peru", "google_ads_geo_targets": ["Peru"]},
    "us": {"name": "Estados Unidos", "google_ads_geo_targets": ["United States"]},
    "sv": {"name": "El Salvador", "google_ads_geo_targets": ["El Salvador"]},
    "gt": {"name": "Guatemala", "google_ads_geo_targets": ["Guatemala"]},
    "hn": {"name": "Honduras", "google_ads_geo_targets": ["Honduras"]},
    "ni": {"name": "Nicaragua", "google_ads_geo_targets": ["Nicaragua"]},
    "cr": {"name": "Costa Rica", "google_ads_geo_targets": ["Costa Rica"]},
    "pa": {"name": "Panama", "google_ads_geo_targets": ["Panama"]},
    "do": {"name": "Republica Dominicana", "google_ads_geo_targets": ["Dominican Republic"]},
    "ec": {"name": "Ecuador", "google_ads_geo_targets": ["Ecuador"]},
    "bo": {"name": "Bolivia", "google_ads_geo_targets": ["Bolivia"]},
    "py": {"name": "Paraguay", "google_ads_geo_targets": ["Paraguay"]},
    "uy": {"name": "Uruguay", "google_ads_geo_targets": ["Uruguay"]},
    "ve": {"name": "Venezuela", "google_ads_geo_targets": ["Venezuela"]},
    "pr": {"name": "Puerto Rico", "google_ads_geo_targets": ["Puerto Rico"]},
}

COUNTRY_ALIASES = {
    "colombia": "co", "co": "co",
    "mexico": "mx", "méxico": "mx", "mx": "mx",
    "espana": "es", "españa": "es", "es": "es", "spain": "es",
    "argentina": "ar", "ar": "ar",
    "chile": "cl", "cl": "cl",
    "peru": "pe", "perú": "pe", "pe": "pe",
    "estados unidos": "us", "usa": "us", "us": "us", "united states": "us",
    "el salvador": "sv", "sv": "sv",
    "guatemala": "gt", "gt": "gt",
    "honduras": "hn", "hn": "hn",
    "nicaragua": "ni", "ni": "ni",
    "costa rica": "cr", "cr": "cr",
    "panama": "pa", "panamá": "pa", "pa": "pa",
    "republica dominicana": "do", "república dominicana": "do", "do": "do", "dominicana": "do",
    "ecuador": "ec", "ec": "ec",
    "bolivia": "bo", "bo": "bo",
    "paraguay": "py", "py": "py",
    "uruguay": "uy", "uy": "uy",
    "venezuela": "ve", "ve": "ve",
    "puerto rico": "pr", "pr": "pr",
}

# HTTP / Requests
HTTP_TIMEOUT = 15
HTTP_MAX_RETRIES = 3
HTTP_RETRY_DELAY = (1, 3)
DELAY_BETWEEN_REQUESTS = (0.5, 1.5)
HTTP_CACHE_TTL_SECONDS = int(os.getenv("HTTP_CACHE_TTL_SECONDS", "86400"))
CACHE_DIR = os.path.join(BASE_DIR, "downloaded_files", "cache")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

# Autocomplete
AUTOCOMPLETE_URL = (
    "https://suggestqueries.google.com/complete/search"
    "?client=firefox&hl={lang}&gl={country}&q={query}"
)

QUESTION_MODIFIERS = [
    "que ",
    "como ",
    "por que ",
    "cuando ",
    "donde ",
    "quien ",
    "cual ",
    "cuanto ",
    "para que ",
    "es ",
]

SEARCH_SUFFIXES = [
    " vs",
    " es",
    " tiene",
    " para",
    " como",
    " en",
    " precio",
    " opiniones",
]

ALPHABET_EXPANSION = list("abcdefghijklmnopqrstuvwxyz")
AUTOCOMPLETE_ALPHABET_LIMIT = int(os.getenv("AUTOCOMPLETE_ALPHABET_LIMIT", "26"))

# Google Search URL
SERP_NUM_RESULTS = int(os.getenv("SERP_NUM_RESULTS", "10"))
SERP_PAGES = int(os.getenv("SERP_PAGES", "2"))
GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}&hl={lang}&gl={country}&num={num}&start={start}"

SERP_DEEP_MODE = int(os.getenv("SERP_DEEP_MODE", "1"))
SERP_QUERY_VARIANT_LIMIT = int(os.getenv("SERP_QUERY_VARIANT_LIMIT", "6"))

_raw_tbm = os.getenv("SERP_TBM_MODES", "").strip()
_tbm_values = [item.strip() for item in _raw_tbm.split(",") if item.strip()] if _raw_tbm else []
if SERP_DEEP_MODE:
    SERP_TBM_MODES = [""] + (_tbm_values if _tbm_values else ["nws", "vid"])
else:
    SERP_TBM_MODES = [""] + _tbm_values if _tbm_values else [""]

# Exportacion
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
EXCEL_TEMPLATE_PATH = os.getenv(
    "EXCEL_TEMPLATE_PATH",
    os.path.join(BASE_DIR, "PLANTILLA CON INFORME.xlsx"),
)

# Google Ads API
GOOGLE_ADS_CONFIG_PATH = os.getenv(
    "GOOGLE_ADS_CONFIGURATION_FILE_PATH",
    os.path.join(BASE_DIR, "google-ads.yaml"),
)
GOOGLE_ADS_FALLBACK_CONFIG_PATH = os.path.join(BASE_DIR, "archivo google-ads.yaml.txt")
GOOGLE_ADS_CUSTOMER_ID_FILE = os.path.join(BASE_DIR, "google-ads.customer-id.txt")
GOOGLE_ADS_CUSTOMER_ID = (
    os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "").strip()
    or _read_optional_value(GOOGLE_ADS_CUSTOMER_ID_FILE).replace("-", "").strip()
)
GOOGLE_ADS_LANGUAGE_CODE = LANG
GOOGLE_ADS_GEO_TARGETS = COUNTRY_CATALOG.get(COUNTRY.lower(), {}).get("google_ads_geo_targets", [])

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = "llama-3.3-70b-versatile"


def normalize_country(user_value: str | None = None) -> dict:
    """Normaliza el pais de la corrida y devuelve sus metadatos."""
    raw_value = (user_value or COUNTRY or "").strip().lower()
    normalized_code = COUNTRY_ALIASES.get(raw_value, raw_value or COUNTRY)
    country_data = COUNTRY_CATALOG.get(normalized_code, COUNTRY_CATALOG[COUNTRY])

    return {
        "country_code": normalized_code,
        "country_name": country_data["name"],
        "google_ads_geo_targets": list(country_data.get("google_ads_geo_targets", [])),
        "language_code": LANG,
    }
