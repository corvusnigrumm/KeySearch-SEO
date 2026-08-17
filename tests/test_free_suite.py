"""
Smoke test para la Suite de Métricas Gratuitas y Multi-Motor de KeySearch.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.multi_engine_suggest import fetch_multi_engine_suggestions
from scraper.volume_estimator import detectar_intencion_y_funnel, estimar_volumenes
from scraper.wikipedia_metrics import obtener_vistas_wikipedia


def test_multi_engine():
    print("--> Testeando Multi-Engine Suggestion Engine...")
    sugs = fetch_multi_engine_suggestions("inteligencia artificial", lang="es", country="co")
    print(f"Total sugerencias multi-motor: {len(sugs)}")
    for k, v in list(sugs.items())[:5]:
        print(f"  - '{k}': Motores={v['engines']} ({v['engine_count']}), Intención={v['intents']}")
    assert isinstance(sugs, dict), "El resultado de sugs debe ser un diccionario"
    print("OK Multi-Engine")


def test_wikipedia_pageviews():
    print("\n--> Testeando Wikipedia Pageviews API (100% gratuita)...")
    res = obtener_vistas_wikipedia("Inteligencia artificial", lang="es")
    if res:
        print(f"  - Artículo: {res['articulo']}")
        print(f"  - Visitas mensuales: {res['visitas_mensuales']:,}")
        print(f"  - Promedio diario: {res['promedio_diario']:,}")
        print(f"  - Período: {res['periodo']}")
    else:
        print("  - Nota: Wikipedia no devolvió datos en este momento (offline/red)")
    print("OK Wikipedia Test")


def test_intent_detection():
    print("\n--> Testeando Detección de Intención & Funnel...")
    ejemplos = [
        "comprar celular samsung",
        "mejores auriculares bluetooth 2026",
        "que es la computacion cuantica",
        "precio suscripcion netflix",
    ]
    for ej in ejemplos:
        intencion, funnel = detectar_intencion_y_funnel(ej)
        print(f"  - '{ej}' -> Intención: {intencion} | Funnel: {funnel}")


def test_volume_estimator_integration():
    print("\n--> Testeando estimar_volumenes con suite gratuita...")
    vol = estimar_volumenes(
        keyword_principal="inteligencia artificial",
        sugerencias=["inteligencia artificial definicion", "inteligencia artificial ejemplos"],
        preguntas_paa=["como funciona la inteligencia artificial"],
        preguntas_autocompletado=["que es la inteligencia artificial"],
        busquedas_relacionadas=["cursos de inteligencia artificial"],
        usar_trends=False,  # rápido sin trends para el test
        search_context={"language_code": "es", "country_code": "co"},
        metadata={"categoria_padre": "Tecnología", "subcategoria": "IA", "referencia": "inteligencia artificial"},
    )
    print(f"Keywords procesadas: {len(vol)}")
    for kw, meta in list(vol.items())[:3]:
        print(
            f"  - '{kw}': Score={meta['score']} ({meta['categoria']}), Intención={meta['intencion']}, Funnel={meta['funnel']}"
        )
    assert len(vol) > 0, "No se generaron métricas"
    print("OK Volume Estimator Test")


if __name__ == "__main__":
    try:
        test_multi_engine()
        test_wikipedia_pageviews()
        test_intent_detection()
        test_volume_estimator_integration()
        print("\n==========================================")
        print(">>> TODOS LOS TESTS DE LA SUITE GRATUITA PASARON EXITOSAMENTE <<<")
        print("==========================================")
    except Exception as e:
        print(f"\n[ERROR] en pruebas: {e}")
        import traceback

        traceback.print_exc()
