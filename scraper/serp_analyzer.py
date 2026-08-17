"""
Módulo Analizador de SERP y Detector de Oportunidades de Oro (SERP Weakness & Low-Hanging Fruits).

Detecta si en los primeros 10 resultados de Google rankean foros (Reddit, Quora),
redes sociales (Pinterest, TikTok) o sitios de baja autoridad, lo cual indica
que Google carece de contenido editorial de calidad sobre el tema y representa
una oportunidad rápida para posicionar en el Top 3.
"""

import re
import urllib.parse

from bs4 import BeautifulSoup

from scraper.utils import limpiar_texto

# Lista de dominios de foros y contenido generado por usuarios (UGC)
FORUM_DOMAINS = {
    "reddit.com",
    "quora.com",
    "forocoches.com",
    "taringa.net",
    "burbuja.info",
    "forosdelweb.com",
    "stackexchange.com",
    "stackoverflow.com",
    "answers.yahoo.com",
    "tripadvisor",
    "meneame.net",
    "discussions.apple.com",
    "community.spotify.com",
    "foro.",
    "foros.",
    "comunidad.",
}

# Redes sociales
SOCIAL_DOMAINS = {
    "pinterest.",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com/pulse",
    "threads.net",
}

# Sitios de bajo filtro / blogs gratuitos
LOW_BARRIER_DOMAINS = {
    "blogspot.com",
    "wordpress.com",
    "wixsite.com",
    "medium.com",
    "scribd.com",
    "issuu.com",
    "slideshare.net",
    "github.com/discussions",
}

# Sitios de máxima autoridad
MAJOR_AUTHORITY_DOMAINS = {
    "wikipedia.org",
    ".gov",
    ".gob.",
    ".edu",
    "amazon.",
    "mercadolibre.",
}


def _extraer_dominio(url: str) -> str:
    """Extrae el dominio limpio de una URL."""
    try:
        if not url:
            return ""
        # Limpiar redirecciones de Google /url?q=...
        if url.startswith("/url?") or "google.com/url" in url:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "q" in parsed and parsed["q"]:
                url = parsed["q"][0]
            elif "url" in parsed and parsed["url"]:
                url = parsed["url"][0]

        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def _clasificar_tipo_dominio(dominio: str, url: str) -> tuple[str, str, str]:
    """
    Clasifica el tipo de dominio.
    Retorna: (categoria_tipo, badge_color, icono)
    """
    dom_low = dominio.lower()
    url_low = url.lower()

    for f_dom in FORUM_DOMAINS:
        if f_dom in dom_low or f_dom in url_low:
            return "Foro / UGC", "bg-amber-100 text-amber-900 border-amber-300", "forum"

    for s_dom in SOCIAL_DOMAINS:
        if s_dom in dom_low or s_dom in url_low:
            return "Red Social", "bg-purple-100 text-purple-900 border-purple-300", "share"

    for l_dom in LOW_BARRIER_DOMAINS:
        if l_dom in dom_low or l_dom in url_low:
            return "Blog Libre / Web 2.0", "bg-sky-100 text-sky-900 border-sky-300", "post_add"

    for a_dom in MAJOR_AUTHORITY_DOMAINS:
        if a_dom in dom_low:
            return "Alta Autoridad / Oficial", "bg-slate-100 text-slate-800 border-slate-300", "verified"

    return "Portal / Editorial", "bg-emerald-50 text-emerald-800 border-emerald-200", "article"


def analizar_debilidades_serp(soup: BeautifulSoup, keyword: str) -> dict:
    """
    Inspecciona los resultados orgánicos del Top 10 en la SERP de Google
    y detecta debilidades y oportunidades de posicionamiento rápido.
    """
    competidores = []
    seen_urls = set()

    # Selectores modernos de resultados orgánicos de Google
    # Google usa div.g, div.tF2Cxc, div.MjjYud, div.yuRUbf, etc.
    candidate_elements = soup.select("div.g, div.tF2Cxc, div.MjjYud, div.yuRUbf, div.Gx5Zad")

    posicion = 1
    for el in candidate_elements:
        # Buscar enlace
        a_tag = el.find("a", href=True)
        if not a_tag:
            continue

        href = a_tag["href"]
        if not href or href.startswith("#") or "google.com" in href or "search?" in href:
            continue

        # Limpiar URL si viene encapsulada
        if href.startswith("/url?") or "google.com/url" in href:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if "q" in parsed and parsed["q"]:
                href = parsed["q"][0]
            elif "url" in parsed and parsed["url"]:
                href = parsed["url"][0]

        if href in seen_urls or not href.startswith("http"):
            continue

        dominio = _extraer_dominio(href)
        if not dominio or "google." in dominio or "youtube.com" in dominio and "/watch" not in href:
            continue

        seen_urls.add(href)

        # Buscar título
        title_tag = el.find(["h3", "h2", "div"], class_=re.compile(r"DKV0Md|LC20lb|vvjwJb", re.I))
        if not title_tag:
            title_tag = a_tag.find(["h3", "h2"])

        titulo = limpiar_texto(title_tag.get_text()) if title_tag else dominio

        # Buscar snippet / descripción
        snippet_tag = el.find("div", class_=re.compile(r"VwiC3b|yXK7lf|MUxGbd|s3v9rd", re.I))
        snippet = limpiar_texto(snippet_tag.get_text()) if snippet_tag else ""

        tipo, badge_color, icono = _clasificar_tipo_dominio(dominio, href)

        competidores.append(
            {
                "posicion": posicion,
                "dominio": dominio,
                "titulo": titulo,
                "url": href,
                "snippet": snippet,
                "tipo": tipo,
                "badge_color": badge_color,
                "icono": icono,
                "es_debilidad": tipo in ("Foro / UGC", "Red Social", "Blog Libre / Web 2.0"),
            }
        )

        posicion += 1
        if len(competidores) >= 10:
            break

    # Si por selectores específicos no encontró 10, hacer fallback con todos los h3 enlazados
    if len(competidores) < 5:
        for h3 in soup.find_all("h3"):
            parent_a = h3.find_parent("a", href=True)
            if not parent_a:
                continue
            href = parent_a["href"]
            if href.startswith("/url?") or "google.com/url" in href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                if "q" in parsed and parsed["q"]:
                    href = parsed["q"][0]
            if href in seen_urls or not href.startswith("http") or "google." in href:
                continue

            dominio = _extraer_dominio(href)
            if not dominio:
                continue

            seen_urls.add(href)
            titulo = limpiar_texto(h3.get_text())
            tipo, badge_color, icono = _clasificar_tipo_dominio(dominio, href)

            competidores.append(
                {
                    "posicion": len(competidores) + 1,
                    "dominio": dominio,
                    "titulo": titulo,
                    "url": href,
                    "snippet": "",
                    "tipo": tipo,
                    "badge_color": badge_color,
                    "icono": icono,
                    "es_debilidad": tipo in ("Foro / UGC", "Red Social", "Blog Libre / Web 2.0"),
                }
            )
            if len(competidores) >= 10:
                break

    # ─── Cálculo de Puntos de Oportunidad y Diagnóstico de SERP ───────────────
    debilidades_detectadas = []
    puntos_oportunidad = 0
    kw_words = set(re.findall(r"\w+", keyword.lower()))
    exact_match_count = 0

    for c in competidores:
        pos = c["posicion"]
        tipo = c["tipo"]
        dom = c["dominio"]
        title_low = c["titulo"].lower()

        # Comprobar si el título contiene la keyword exacta
        if keyword.lower() in title_low:
            exact_match_count += 1

        if tipo == "Foro / UGC":
            if pos <= 3:
                puntos_oportunidad += 45
                debilidades_detectadas.append(f"🏆 Foro '{dom}' rankea en posición #{pos} (Top 3) - ¡Gran oportunidad!")
            elif pos <= 5:
                puntos_oportunidad += 30
                debilidades_detectadas.append(f"⭐ Foro '{dom}' rankea en posición #{pos} (Top 5)")
            else:
                puntos_oportunidad += 15
                debilidades_detectadas.append(f"Foro '{dom}' detectado en posición #{pos}")

        elif tipo == "Red Social":
            if pos <= 5:
                puntos_oportunidad += 25
                debilidades_detectadas.append(f"Red social '{dom}' rankea en posición #{pos}")
            else:
                puntos_oportunidad += 10

        elif tipo == "Blog Libre / Web 2.0":
            if pos <= 5:
                puntos_oportunidad += 20
                debilidades_detectadas.append(f"Blog de baja autoridad '{dom}' en posición #{pos}")
            else:
                puntos_oportunidad += 10

    # Evaluación de Exact Match Titles
    if competidores and exact_match_count <= 2:
        puntos_oportunidad += 20
        debilidades_detectadas.append(
            f"Solo {exact_match_count} de {len(competidores)} competidores tienen la keyword exacta en su título."
        )

    # Clasificación final
    if puntos_oportunidad >= 45:
        nivel_oportunidad = "Oportunidad de Oro"
        dificultad_estimada = "Muy Fácil (Baja Competencia)"
        badge_estilo = "bg-amber-100 text-amber-900 border-amber-400 font-bold"
        icono_resumen = "military_tech"
        resumen_editorial = "Google carece de contenido especializado suficiente y posiciona foros o redes en primeros puestos. Un artículo optimizado puede alcanzar el Top 3 rápidamente."
    elif puntos_oportunidad >= 25:
        nivel_oportunidad = "Oportunidad Alta"
        dificultad_estimada = "Fácil - Moderada"
        badge_estilo = "bg-emerald-100 text-emerald-900 border-emerald-400 font-bold"
        icono_resumen = "trending_up"
        resumen_editorial = "Existen resultados débiles en la primera página. Posicionar en el Top 5 es muy viable con contenido completo y buen enlazado."
    elif puntos_oportunidad >= 10:
        nivel_oportunidad = "Oportunidad Media"
        dificultad_estimada = "Moderada"
        badge_estilo = "bg-sky-100 text-sky-900 border-sky-400"
        icono_resumen = "speed"
        resumen_editorial = "Competencia balanceada con algunos blogs y medios. Requiere cubrir a fondo las preguntas PAA y superar el recuento de palabras."
    else:
        nivel_oportunidad = "Competencia Alta"
        dificultad_estimada = "Difícil (Medios de Alta Autoridad)"
        badge_estilo = "bg-slate-100 text-slate-800 border-slate-300"
        icono_resumen = "shield"
        resumen_editorial = "La SERP está dominada por marcas oficiales y portales de alta autoridad. Se recomienda apuntar a variantes long-tail más específicas."

    return {
        "competidores": competidores,
        "total_analizados": len(competidores),
        "puntos_oportunidad": puntos_oportunidad,
        "nivel_oportunidad": nivel_oportunidad,
        "dificultad_estimada": dificultad_estimada,
        "badge_estilo": badge_estilo,
        "icono_resumen": icono_resumen,
        "resumen_editorial": resumen_editorial,
        "debilidades_detectadas": debilidades_detectadas,
        "exact_match_count": exact_match_count,
        "es_oportunidad_oro": puntos_oportunidad >= 45,
    }
