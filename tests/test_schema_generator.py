"""
Test para el Generador de Schema JSON-LD y Meta Tags de Alto CTR.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.ai_generator import generar_schema_y_meta_tags


def test_schema_generation():
    print("--> Testeando Generador de Schema JSON-LD & Meta Tags...")
    kw = "curso de marketing digital"
    preguntas = [
        "que se aprende en un curso de marketing digital",
        "cuanto dura un curso de marketing digital",
        "cuanto cuesta un curso de marketing digital",
        "vale la pena estudiar marketing digital",
    ]

    res = generar_schema_y_meta_tags(kw, preguntas, pais="Colombia")
    print(f"\n[Meta Title]: {res['meta_title']} ({len(res['meta_title'])} caracteres)")
    print(f"[Meta Desc]: {res['meta_description']} ({len(res['meta_description'])} caracteres)")
    print(f"[Slug]: {res['slug_sugerido']}")
    print(f"[Títulos Alternativos]: {res['meta_titles_alternativos']}")
    print(f"[FAQs en Schema]: {len(res['faq_items'])}")
    print(f"\n[Schema String Sample]:\n{res['schema_faq_string'][:200]}...")

    assert len(res['meta_title']) <= 65, "Meta Title demasiado largo"
    assert len(res['meta_description']) <= 165, "Meta Description demasiado larga"
    assert "FAQPage" in res['schema_faq_string'], "El Schema no contiene FAQPage"
    print("\n>>> TEST DE SCHEMA Y META TAGS EXITOSO <<<")


if __name__ == "__main__":
    test_schema_generation()
