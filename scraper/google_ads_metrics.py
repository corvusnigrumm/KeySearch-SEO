"""
Integracion opcional con Google Ads API para metricas historicas reales.

Si el usuario configura google-ads.yaml y GOOGLE_ADS_CUSTOMER_ID, este modulo
enriquece los terminos con:
- promedio de busquedas mensuales
- competencia
- indice de competencia
- pujas de top of page
- volumen mensual por mes
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from config import (
    GOOGLE_ADS_CONFIG_PATH,
    GOOGLE_ADS_CUSTOMER_ID,
    GOOGLE_ADS_FALLBACK_CONFIG_PATH,
    GOOGLE_ADS_GEO_TARGETS,
    GOOGLE_ADS_LANGUAGE_CODE,
)

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    HAS_GOOGLE_ADS_LIB = True
except ImportError:
    HAS_GOOGLE_ADS_LIB = False
    GoogleAdsClient = None
    GoogleAdsException = Exception


KEYWORD_BATCH_SIZE = 200


def _existing_config_path() -> Optional[str]:
    for path in (GOOGLE_ADS_CONFIG_PATH, GOOGLE_ADS_FALLBACK_CONFIG_PATH):
        if path and os.path.exists(path):
            return path
    return None


def get_google_ads_status() -> dict:
    """Describe si Google Ads esta listo para usarse o no."""
    if not HAS_GOOGLE_ADS_LIB:
        return {
            "enabled": False,
            "reason": "Falta instalar la libreria oficial google-ads",
            "config_path": None,
        }

    config_path = _existing_config_path()
    if not config_path:
        return {
            "enabled": False,
            "reason": "No se encontro google-ads.yaml local",
            "config_path": None,
        }

    if not GOOGLE_ADS_CUSTOMER_ID:
        return {
            "enabled": False,
            "reason": "Falta definir GOOGLE_ADS_CUSTOMER_ID",
            "config_path": config_path,
        }

    return {
        "enabled": True,
        "reason": "Google Ads listo",
        "config_path": config_path,
    }


def _load_client(config_path: str):
    return GoogleAdsClient.load_from_storage(path=config_path)


def _resolve_language_resource_name(client, customer_id: str, language_code: str) -> Optional[str]:
    google_ads_service = client.get_service("GoogleAdsService")
    query = (
        "SELECT language_constant.resource_name "
        f"FROM language_constant WHERE language_constant.code = '{language_code}' LIMIT 1"
    )
    rows = google_ads_service.search(customer_id=customer_id, query=query)
    for row in rows:
        return row.language_constant.resource_name
    return None


def _resolve_geo_target_constants(client, target_names: List[str]) -> List[str]:
    if not target_names:
        return []

    geo_service = client.get_service("GeoTargetConstantService")
    location_names = client.get_type("LocationNames")
    location_names.names.extend(target_names)

    request = client.get_type("SuggestGeoTargetConstantsRequest")
    request.locale = GOOGLE_ADS_LANGUAGE_CODE
    request.location_names = location_names

    response = geo_service.suggest_geo_target_constants(request=request)

    resource_names = []
    for suggestion in response.geo_target_constant_suggestions:
        resource_name = suggestion.geo_target_constant.resource_name
        if resource_name not in resource_names:
            resource_names.append(resource_name)
    return resource_names


def _competition_name(value) -> str:
    if hasattr(value, "name"):
        return value.name
    return str(value)


def _normalize_keyword(text: str) -> str:
    return " ".join((text or "").lower().split())


def _update_metric(metric: dict, result) -> None:
    monthly_searches = []
    for item in result.keyword_metrics.monthly_search_volumes:
        monthly_searches.append(
            {
                "year": int(item.year),
                "month": int(item.month),
                "monthly_searches": int(item.monthly_searches),
            }
        )

    monthly_searches.sort(key=lambda row: (row["year"], row["month"]), reverse=True)

    metric["google_ads_keyword_text"] = result.text
    metric["google_ads_close_variants"] = list(result.close_variants)
    metric["google_ads_avg_monthly_searches"] = (
        int(result.keyword_metrics.avg_monthly_searches)
        if result.keyword_metrics.avg_monthly_searches is not None
        else None
    )
    metric["google_ads_competition"] = _competition_name(result.keyword_metrics.competition)
    metric["google_ads_competition_index"] = (
        int(result.keyword_metrics.competition_index)
        if result.keyword_metrics.competition_index is not None
        else None
    )
    metric["google_ads_low_top_of_page_bid_micros"] = (
        int(result.keyword_metrics.low_top_of_page_bid_micros)
        if result.keyword_metrics.low_top_of_page_bid_micros is not None
        else None
    )
    metric["google_ads_high_top_of_page_bid_micros"] = (
        int(result.keyword_metrics.high_top_of_page_bid_micros)
        if result.keyword_metrics.high_top_of_page_bid_micros is not None
        else None
    )
    metric["google_ads_monthly_search_volumes"] = monthly_searches


def enrich_with_google_ads_metrics(metricas: Dict[str, dict], progress_callback=None) -> dict:
    """Enriquece las metricas con datos historicos reales de Google Ads."""
    status = get_google_ads_status()
    if not status["enabled"]:
        if progress_callback:
            progress_callback(f"Google Ads omitido: {status['reason']}")
        return {
            "enabled": False,
            "keywords_enriched": 0,
            "reason": status["reason"],
            "config_path": status.get("config_path"),
        }

    config_path = status["config_path"]
    customer_id = GOOGLE_ADS_CUSTOMER_ID
    geo_targets = []
    for metrica in metricas.values():
        geo_targets = metrica.get("google_ads_geo_targets", [])
        if geo_targets:
            break

    try:
        client = _load_client(config_path)
        language_resource_name = _resolve_language_resource_name(
            client, customer_id, GOOGLE_ADS_LANGUAGE_CODE
        )
        geo_target_constants = _resolve_geo_target_constants(
            client,
            geo_targets or GOOGLE_ADS_GEO_TARGETS,
        )

        keyword_plan_service = client.get_service("KeywordPlanIdeaService")
        network_enum = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH

        normalized_lookup: Dict[str, List[str]] = {}
        for original in metricas.keys():
            normalized_lookup.setdefault(_normalize_keyword(original), []).append(original)

        enriched = 0
        keywords = list(metricas.keys())

        for offset in range(0, len(keywords), KEYWORD_BATCH_SIZE):
            batch = keywords[offset:offset + KEYWORD_BATCH_SIZE]
            if progress_callback:
                progress_callback(
                    f"Google Ads: lote {offset // KEYWORD_BATCH_SIZE + 1}/{(len(keywords) + KEYWORD_BATCH_SIZE - 1) // KEYWORD_BATCH_SIZE}..."
                )

            request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
            request.customer_id = customer_id
            request.keywords.extend(batch)
            request.keyword_plan_network = network_enum

            if language_resource_name:
                request.language = language_resource_name
            if geo_target_constants:
                request.geo_target_constants.extend(geo_target_constants)

            response = keyword_plan_service.generate_keyword_historical_metrics(request=request)

            for result in response.results:
                aliases = {_normalize_keyword(result.text)}
                aliases.update(_normalize_keyword(item) for item in result.close_variants)

                matched = False
                for alias in aliases:
                    for original in normalized_lookup.get(alias, []):
                        _update_metric(metricas[original], result)
                        matched = True

                if matched:
                    enriched += 1

        if progress_callback:
            progress_callback(f"Google Ads OK: {enriched} keywords con metricas historicas")

        return {
            "enabled": True,
            "keywords_enriched": enriched,
            "reason": "Metricas historicas obtenidas",
            "config_path": config_path,
        }

    except GoogleAdsException as exc:
        message = f"Error de Google Ads API: {exc}"
        if progress_callback:
            progress_callback(message)
        return {
            "enabled": False,
            "keywords_enriched": 0,
            "reason": message,
            "config_path": config_path,
        }
    except Exception as exc:
        message = f"Error inesperado con Google Ads: {exc}"
        if progress_callback:
            progress_callback(message)
        return {
            "enabled": False,
            "keywords_enriched": 0,
            "reason": message,
            "config_path": config_path,
        }
