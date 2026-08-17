"""
Módulo Estimador de Keyword Golden Ratio (KGR).

La metodología KGR (Keyword Golden Ratio) permite identificar términos de cola larga
donde la cantidad de sitios web que han optimizado su etiqueta <title> es inferior a la demanda.

Fórmula:
  KGR = (Resultados allintitle) / (Volumen de Demanda / Score de Oportunidad)

Rangos:
  - KGR < 0.25: ⭐ Oportunidad de Oro KGR (Rankea en Top 10 en días)
  - 0.25 <= KGR <= 1.00: 🟢 Competencia Baja - Media
  - KGR > 1.00: 🔴 Término Saturado
"""


def estimar_kgr(
    keyword: str,
    score_demanda: float = 50.0,
    exact_match_serp_count: int = 0,
    volumen_mensual: int | None = None,
) -> dict:
    """
    Calcula la métrica KGR para una keyword a partir de la presencia de títulos
    exactos en Google y la demanda relativa.
    """
    num_palabras = len(keyword.strip().split())
    # Base de títulos exactos estimada o calculada
    # Si tenemos exact_match_serp_count de la primera página (0-10):
    titulos_exactos_estimados = max(
        1, exact_match_serp_count * 12 if num_palabras >= 4 else (exact_match_serp_count + 1) * 35
    )

    base_volumen = volumen_mensual if (volumen_mensual and volumen_mensual > 0) else max(30, int(score_demanda * 10))

    kgr_ratio = round(titulos_exactos_estimados / max(10, base_volumen), 2)

    if kgr_ratio < 0.25:
        veredicto = "Oportunidad de Oro KGR"
        badge_cls = "bg-amber-100 text-amber-900 border-amber-400 font-bold"
        explicacion = "Muy pocos sitios en internet usan este título exacto. Excelente para rankear en primera página en tiempo récord."
        icono = "military_tech"
    elif kgr_ratio <= 1.00:
        veredicto = "KGR Viable (Competencia Baja)"
        badge_cls = "bg-emerald-100 text-emerald-900 border-emerald-400 font-bold"
        explicacion = "Buen balance entre demanda y competencia. Posicionable con un artículo bien optimizado."
        icono = "trending_up"
    else:
        veredicto = "KGR Alto (Competitivo)"
        badge_cls = "bg-slate-100 text-slate-700 border-slate-300"
        explicacion = (
            "Muchos sitios compiten con títulos similares. Se recomienda enfocarse en variantes con KGR < 0.25."
        )
        icono = "shield"

    return {
        "keyword": keyword,
        "kgr_ratio": kgr_ratio,
        "veredicto": veredicto,
        "badge_cls": badge_cls,
        "icono": icono,
        "explicacion": explicacion,
        "titulos_exactos_estimados": titulos_exactos_estimados,
        "base_volumen": base_volumen,
        "es_kgr_oro": kgr_ratio < 0.25,
    }
