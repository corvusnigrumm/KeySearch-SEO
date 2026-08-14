"""
Test del Filtro de Coherencia Semántica y Sentido Real de Búsquedas.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.ai_filter import filtrar_con_ia, _filtro_determinista


def test_semantic_sense_filter():
    kw = "terremoto en colombia"
    sample_queries = [
        "terremoto en colombia hoy",
        "terremoto en colombia donde fue",
        "terremoto en colombia magnitud",
        "terremoto en colombia gratis online",  # Incongruente / absurdo
        "terremoto en colombia precio",         # Incongruente / absurdo
        "terremoto en colombia comprar",        # Incongruente / absurdo
        "terremoto en colombia barato",         # Incongruente / absurdo
        "terremoto en colombia descargar pdf gratis", # Incongruente / absurdo
        "terremoto en colombia ultimas noticias",
        "terremoto en colombia servicio geologico nacional",
    ]

    print("\n1. Testeando Filtro Determinista para 'terremoto en colombia'...")
    det_filtered = _filtro_determinista(sample_queries, kw)
    print(f"Originales: {len(sample_queries)} -> Filtradas: {len(det_filtered)}")
    for q in det_filtered:
        print(f"  [OK] Conservada: {q}")

    assert "terremoto en colombia gratis online" not in det_filtered, "Falló: 'terremoto en colombia gratis online' no fue eliminada"
    assert "terremoto en colombia precio" not in det_filtered, "Falló: 'terremoto en colombia precio' no fue eliminada"
    assert "terremoto en colombia comprar" not in det_filtered, "Falló: 'terremoto en colombia comprar' no fue eliminada"
    assert "terremoto en colombia hoy" in det_filtered, "Falló: 'terremoto en colombia hoy' debió ser conservada"
    assert "terremoto en colombia donde fue" in det_filtered, "Falló: 'donde fue' debió ser conservada"

    print("\n2. Testeando Pipeline Completo filtrar_con_ia...")
    final_filtered = filtrar_con_ia(sample_queries, kw, pais="Colombia")
    print(f"Final tras IA: {len(final_filtered)} items")
    for q in final_filtered:
        print(f"  [OK] {q}")

    assert "terremoto en colombia gratis online" not in final_filtered
    print("\n>>> TEST DE COHERENCIA SEMANTICA Y SENTIDO REAL PASO EXITOSAMENTE <<<")


if __name__ == "__main__":
    test_semantic_sense_filter()
