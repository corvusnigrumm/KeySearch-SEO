"""
Exportador de resultados a JSON.

El JSON expone solo datos trazables y separa claramente la prioridad interna
de las metricas reales de Google.
"""
import json
import os
from datetime import datetime
from typing import Dict, List

from config import OUTPUT_DIR
from scraper.utils import generar_nombre_archivo


def exportar_json(keyword: str, datos: Dict[str, List[str]]) -> str:
    """Exporta los resultados a un archivo JSON estructurado."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    volumenes = datos.get("volumenes", {})
    google_ads = datos.get("google_ads", {}) or {}
    google_ads_activo = google_ads.get("enabled") and google_ads.get("keywords_enriched", 0) > 0

    def _con_metricas(items: List[str]) -> List[dict]:
        resultado = []
        for item in items:
            vol = volumenes.get(item, {})
            resultado.append(
                {
                    "texto": item,
                    "pais": vol.get("pais"),
                    "pais_codigo": vol.get("pais_codigo"),
                    "categoria": vol.get("categoria_padre"),
                    "subcategoria": vol.get("subcategoria"),
                    "referencia": vol.get("referencia"),
                    "score_prioridad": vol.get("score", 0),
                    "prioridad": vol.get("categoria", "-"),
                    "fuente_principal": vol.get("fuente"),
                    "posicion_fuente": vol.get("posicion_fuente"),
                    "fuentes_detectadas": vol.get("fuentes", []),
                    "google_ads_keyword_text": vol.get("google_ads_keyword_text"),
                    "google_ads_close_variants": vol.get("google_ads_close_variants", []),
                    "google_ads_avg_monthly_searches": vol.get("google_ads_avg_monthly_searches"),
                    "google_ads_competition": vol.get("google_ads_competition"),
                    "google_ads_competition_index": vol.get("google_ads_competition_index"),
                    "google_ads_low_top_of_page_bid_micros": vol.get("google_ads_low_top_of_page_bid_micros"),
                    "google_ads_high_top_of_page_bid_micros": vol.get("google_ads_high_top_of_page_bid_micros"),
                    "google_ads_monthly_search_volumes": vol.get("google_ads_monthly_search_volumes", []),
                    "google_trends_promedio_12m": vol.get("google_trends_promedio"),
                    "google_trends_pico_12m": vol.get("google_trends_pico"),
                    "google_trends_ultimo_punto": vol.get("google_trends_ultimo"),
                    "google_trends_timeframe": vol.get("google_trends_timeframe"),
                    "google_trends_geo": vol.get("google_trends_geo"),
                    "volumen_mensual_exacto": None,
                }
            )

        resultado.sort(key=lambda item: item["score_prioridad"], reverse=True)
        return resultado

    resultado = {
        "keyword": keyword,
        "fecha": datetime.now().isoformat(),
        "pais": datos.get("country_name"),
        "pais_codigo": datos.get("country_code"),
        "categoria": datos.get("category_name"),
        "subcategoria": datos.get("subcategory_name"),
        "modo_reporte": (
            "google_ads_trends_observable_signals"
            if google_ads_activo
            else "trends_observable_signals"
        ),
        "metodologia": {
            "usa_datos_reales_de_google": True,
            "incluye_volumen_mensual_exacto": False,
            "google_ads_activo": google_ads_activo,
            "google_ads_estado": google_ads.get("reason"),
            "descripcion": (
                "El reporte conserva solo datos trazables de Google: fuente, posicion dentro de la "
                "fuente y, cuando esta disponible, Google Ads historico y Google Trends 0-100. "
                "El score es una prioridad interna para ordenar temas."
            ),
            "uso_recomendado": (
                "Priorizacion editorial, investigacion SEO y deteccion de preguntas reales. "
                "No usar para forecasting financiero ni presupuestos de medios."
            ),
        },
        "estadisticas": {
            "total_sugerencias": len(datos.get("sugerencias", [])),
            "total_preguntas_paa": len(datos.get("preguntas_paa", [])),
            "total_preguntas_autocompletado": len(datos.get("preguntas_autocompletado", [])),
            "total_busquedas_relacionadas": len(datos.get("busquedas_relacionadas", [])),
            "total_keywords_con_google_ads": sum(
                1 for item in volumenes.values() if item.get("google_ads_avg_monthly_searches") is not None
            ),
            "total_keywords_con_trends": sum(
                1 for item in volumenes.values() if item.get("google_trends_promedio") is not None
            ),
        },
        "sugerencias": _con_metricas(datos.get("sugerencias", [])),
        "preguntas_paa": _con_metricas(datos.get("preguntas_paa", [])),
        "preguntas_autocompletado": _con_metricas(datos.get("preguntas_autocompletado", [])),
        "busquedas_relacionadas": _con_metricas(datos.get("busquedas_relacionadas", [])),
    }

    nombre = generar_nombre_archivo(keyword, "json")
    ruta = os.path.join(OUTPUT_DIR, nombre)

    with open(ruta, "w", encoding="utf-8") as file_handle:
        json.dump(resultado, file_handle, ensure_ascii=False, indent=2)

    return ruta
