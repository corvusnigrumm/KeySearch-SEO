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
APP_NAME = "KeySearch Diarrea de Perro con Sangre sin Coagular"
APP_VERSION = "6.0"


def _read_optional_value(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as file_handle:
        return file_handle.read().strip()


def _resolve_template_path() -> str:
    """
    Resuelve la plantilla Excel priorizando:
    1) EXCEL_TEMPLATE_PATH en entorno
    2) Junto al ejecutable/proyecto (BASE_DIR)
    3) Recursos embebidos de PyInstaller (_MEIPASS)
    """
    env_value = os.getenv("EXCEL_TEMPLATE_PATH", "").strip()
    if env_value and os.path.exists(env_value):
        return env_value

    filename = "PLANTILLA CON INFORME.xlsx"
    candidate_base = os.path.join(BASE_DIR, filename)
    if os.path.exists(candidate_base):
        return candidate_base

    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidate_meipass = os.path.join(meipass, filename)
        if os.path.exists(candidate_meipass):
            return candidate_meipass

    # Fallback final (mantiene comportamiento previo)
    return candidate_base


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
HTTP_TIMEOUT = 20
HTTP_MAX_RETRIES = 4
HTTP_RETRY_DELAY = (3, 8)
DELAY_BETWEEN_REQUESTS = (2.0, 5.0)
HTTP_CACHE_TTL_SECONDS = int(os.getenv("HTTP_CACHE_TTL_SECONDS", "86400"))
CACHE_DIR = os.path.join(BASE_DIR, "downloaded_files", "cache")
SERP_MIN_REQUEST_INTERVAL = (
    float(os.getenv("SERP_MIN_REQUEST_INTERVAL_MIN", "4.0")),
    float(os.getenv("SERP_MIN_REQUEST_INTERVAL_MAX", "8.0")),
)
SERP_429_BREAKER_THRESHOLD = int(os.getenv("SERP_429_BREAKER_THRESHOLD", "2"))
SERP_429_BREAKER_COOLDOWN = (
    float(os.getenv("SERP_429_BREAKER_COOLDOWN_MIN", "120.0")),
    float(os.getenv("SERP_429_BREAKER_COOLDOWN_MAX", "240.0")),
)

# Pool amplio de User-Agents reales con versiones modernas (2024-2025)
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Firefox macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:138.0) Gecko/20100101 Firefox/138.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
]

# Perfiles de headers completos (cada UA tiene su sec-ch-ua correspondiente)
USER_AGENT_PROFILES = [
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-mobile": "?0",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="135", "Google Chrome";v="135", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-mobile": "?0",
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="135", "Google Chrome";v="135", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
    },
    {
        "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"Linux"',
        "sec-ch-ua-mobile": "?0",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
        "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-mobile": "?0",
    },
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
SCRAPE_PROFILE = os.getenv("SCRAPE_PROFILE", "normal").strip().lower()
IS_EXTREME_PROFILE = SCRAPE_PROFILE in {"extreme", "ultra", "max"}

AUTOCOMPLETE_DEEP_EXPANSION_LIMIT = int(
    os.getenv("AUTOCOMPLETE_DEEP_EXPANSION_LIMIT", "200" if IS_EXTREME_PROFILE else "60")
)
AUTOCOMPLETE_DEEP_RELATED_ROUNDS = int(
    os.getenv("AUTOCOMPLETE_DEEP_RELATED_ROUNDS", "8" if IS_EXTREME_PROFILE else "4")
)
AUTOCOMPLETE_DEEP_MIN_DELAY = float(
    os.getenv("AUTOCOMPLETE_DEEP_MIN_DELAY", "0.4" if IS_EXTREME_PROFILE else "0.3")
)
AUTOCOMPLETE_DEEP_MAX_DELAY = float(
    os.getenv("AUTOCOMPLETE_DEEP_MAX_DELAY", "1.0" if IS_EXTREME_PROFILE else "0.95")
)
AUTOCOMPLETE_PAA_RECURSIVE_DEPTH = int(
    os.getenv("AUTOCOMPLETE_PAA_RECURSIVE_DEPTH", "5" if IS_EXTREME_PROFILE else "2")
)
AUTOCOMPLETE_RELATED_RECURSIVE_DEPTH = int(
    os.getenv("AUTOCOMPLETE_RELATED_RECURSIVE_DEPTH", "5" if IS_EXTREME_PROFILE else "2")
)
AUTOCOMPLETE_DEEP_SEED_LIMIT = int(
    os.getenv("AUTOCOMPLETE_DEEP_SEED_LIMIT", "400" if IS_EXTREME_PROFILE else "80")
)

# Google Search URL
# IMPORTANTE: Mantener SERP_NUM_RESULTS bajo y SERP_PAGES en 1.
# Con 6 variantes x 3 modos x 2 páginas = 36 requests → Google bloquea siempre.
# Con 2 variantes x 1 modo x 1 página = 2 requests → nivel de bloqueo bajo.
SERP_NUM_RESULTS = int(os.getenv("SERP_NUM_RESULTS", "10"))
SERP_PAGES = int(os.getenv("SERP_PAGES", "3" if IS_EXTREME_PROFILE else "1"))
GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}&hl={lang}&gl={country}&num={num}&start={start}"

SERP_DEEP_MODE = int(os.getenv("SERP_DEEP_MODE", "1" if IS_EXTREME_PROFILE else "0"))
SERP_QUERY_VARIANT_LIMIT = int(os.getenv("SERP_QUERY_VARIANT_LIMIT", "6" if IS_EXTREME_PROFILE else "2"))

# Sin modos tbm (nws, vid) por defecto → multiplican las peticiones x3
_raw_tbm = os.getenv("SERP_TBM_MODES", "").strip()
_tbm_values = [item.strip() for item in _raw_tbm.split(",") if item.strip()] if _raw_tbm else []
if SERP_DEEP_MODE:
    SERP_TBM_MODES = [""] + (_tbm_values if _tbm_values else [])
else:
    SERP_TBM_MODES = [""]  # Solo búsqueda normal, sin news/video


# Exportacion
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
EXCEL_TEMPLATE_PATH = _resolve_template_path()

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
