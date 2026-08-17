"""
Test para el Generador de Content Brief Editorial y el Estimador de KGR.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.content_brief import exportar_content_brief_markdown, generar_content_brief
from scraper.kgr_estimator import estimar_kgr


def test_content_brief_and_kgr():
    print("--> Testeando Generador de Content Brief Editorial...")
    kw = "como crear una pagina web"
    sugs = [
        "como crear una pagina web gratis",
        "como crear una pagina web profesional",
        "como crear una pagina web con wordpress",
    ]
    paas = ["cuanto cuesta crear una pagina web", "que se necesita para crear una pagina web"]

    brief = generar_content_brief(
        kw, sugerencias=sugs, preguntas_paa=paas, pais="Colombia", intencion="Informativa / Comercial"
    )

    print(f"\n[Meta H1]: {brief['meta_h1']}")
    print(f"[Longitud]: {brief['longitud_recomendada_palabras']}")
    print(f"[Formato]: {brief['formato_sugerido']}")
    print(f"[Total H2]: {len(brief['secciones_h2'])}")
    for sec in brief["secciones_h2"]:
        print(f"  - H2: {sec['h2']} (H3s: {len(sec.get('h3_subsecciones', []))})")

    md_brief = exportar_content_brief_markdown(brief)
    assert len(md_brief) > 100, "Markdown brief vacío"
    assert "Content Brief" in md_brief, "Falta cabecera en brief markdown"
    print("\nOK Content Brief")

    print("\n--> Testeando Estimador de KGR (Keyword Golden Ratio)...")
    kgr_res = estimar_kgr("como crear una pagina web gratis paso a paso", score_demanda=80.0, exact_match_serp_count=1)
    print(f"  - Keyword: {kgr_res['keyword']}")
    print(f"  - KGR Ratio: {kgr_res['kgr_ratio']}")
    print(f"  - Veredicto: {kgr_res['veredicto']}")
    print(f"  - Es Oro: {kgr_res['es_kgr_oro']}")

    assert "kgr_ratio" in kgr_res, "Falta kgr_ratio"
    print("\n>>> TODOS LOS TESTS DE CONTENT BRIEF Y KGR PASARON EXITOSAMENTE <<<")


if __name__ == "__main__":
    test_content_brief_and_kgr()
