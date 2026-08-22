"""
Test para el Generador de Copies de Ads y Hooks Virales (v2: intent-driven).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.ai_generator import generar_copywriting_ads_y_hooks


def test_ads_copywriting():
    print("--> Testeando Generador de Copies de Ads & Hooks (v2)...")
    kw = "curso de inteligencia artificial"
    sugerencias = [
        "curso de inteligencia artificial",
        "como aprender ia desde cero",
        "mejores cursos de ia online",
        "curso ia con certificado",
        "inteligencia artificial para principiantes",
    ]

    res = generar_copywriting_ads_y_hooks(
        kw, pais="Colombia", intencion="comercial", sugerencias=sugerencias,
    )

    print(f"\n[Ad Hooks ({len(res['ad_hooks'])})]:")
    for h in res["ad_hooks"]:
        print(f"  - {h}")

    print(f"\n[Ads Headlines ({len(res['ads_headline'])})]:")
    for t in res["ads_headline"]:
        print(f"  - '{t}' ({len(t)} car)")

    print(f"\n[Ads Descriptions ({len(res['ads_description'])})]:")
    for d in res["ads_description"]:
        print(f"  - '{d}' ({len(d)} car)")

    print(f"\n[CTA]: {res['cta_sugerido']}")
    print(f"[Propuesta Valor]: {res['propuesta_valor']}")

    assert len(res["ad_hooks"]) == 6, f"Deben haber 6 hooks, hay {len(res['ad_hooks'])}"
    assert len(res["ads_headline"]) == 5, f"Deben haber 5 headlines, hay {len(res['ads_headline'])}"
    assert len(res["ads_description"]) == 5, f"Deben haber 5 descriptions, hay {len(res['ads_description'])}"
    assert res["cta_sugerido"], "cta_sugerido no debe estar vacio"
    assert res["propuesta_valor"], "propuesta_valor no debe estar vacio"

    print("\n>>> TEST DE ADS COPYWRITING Y HOOKS EXITOSO <<<")


if __name__ == "__main__":
    test_ads_copywriting()
