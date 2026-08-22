"""
Test para el Generador de Schema JSON-LD y Meta Tags de Alto CTR (v2: multi-type schemas).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.ai_generator import generar_schema_y_meta_tags


def test_schema_generation():
    print("--> Testeando Generador de Schema JSON-LD & Meta Tags (v2)...")
    kw = "curso de marketing digital"
    top_kws = [
        "curso de marketing digital",
        "como aprender marketing digital",
        "mejor curso de marketing digital",
        "curso marketing digital online",
        "cuanto cuesta curso marketing digital",
    ]

    res = generar_schema_y_meta_tags(kw, pais="Colombia", top_keywords=top_kws, intencion="comercial")
    print(f"\n[Meta Title]: {res['meta_title']} ({len(res['meta_title'])} caracteres)")
    print(f"[Meta Desc]: {res['meta_description']} ({len(res['meta_description'])} caracteres)")
    print(f"[Slug]: {res['slug']}")
    print(f"[Schema All String length]: {len(res['schema_all_string'])}")

    assert res["meta_title"], "meta_title no debe estar vacio"
    assert res["meta_description"], "meta_description no debe estar vacio"
    assert res["slug"], "slug no debe estar vacio"
    assert len(res["meta_title"]) <= 65, "Meta Title demasiado largo"
    assert len(res["meta_description"]) <= 165, "Meta Description demasiado larga"

    has_any_schema = (
        res.get("schema_faq_json") is not None
        or res.get("schema_article_json") is not None
        or res.get("schema_breadcrumb_json") is not None
    )
    print(f"[Has any schema]: {has_any_schema}")
    assert has_any_schema, "Debe generar al menos un schema (Article o FAQPage)"
    print("\n>>> TEST DE SCHEMA Y META TAGS EXITOSO <<<")


if __name__ == "__main__":
    test_schema_generation()
