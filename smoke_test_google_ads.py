"""
Prueba rapida de Google Ads API usando la integracion del proyecto.
"""
from scraper.google_ads_metrics import enrich_with_google_ads_metrics, get_google_ads_status


def main() -> int:
    status = get_google_ads_status()
    print("STATUS:", status)

    metricas = {
        "marketing digital": {
            "score": 100.0,
            "categoria": "Muy alta",
            "fuente": "Autocompletado",
            "posicion_fuente": 1,
            "fuentes": ["Autocompletado"],
            "trends": None,
            "google_trends_promedio": None,
            "google_trends_pico": None,
            "google_trends_ultimo": None,
            "google_trends_timeframe": None,
            "google_trends_geo": None,
            "google_ads_keyword_text": None,
            "google_ads_close_variants": [],
            "google_ads_avg_monthly_searches": None,
            "google_ads_competition": None,
            "google_ads_competition_index": None,
            "google_ads_low_top_of_page_bid_micros": None,
            "google_ads_high_top_of_page_bid_micros": None,
            "google_ads_monthly_search_volumes": [],
        }
    }

    result = enrich_with_google_ads_metrics(metricas, progress_callback=print)
    print("RESULT:", result)
    print("METRICS:", metricas["marketing digital"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
