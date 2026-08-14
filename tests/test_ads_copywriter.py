"""
Test para el Generador de Copies de Ads y Hooks Virales.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.ai_filter import generar_copywriting_ads_y_hooks


def test_ads_copywriting():
    print("--> Testeando Generador de Copies de Ads & Hooks...")
    kw = "curso de inteligencia artificial"
    preguntas = [
        "como aprender inteligencia artificial desde cero",
        "cuanto cuesta un curso de ia",
        "los mejores cursos de inteligencia artificial online",
    ]

    res = generar_copywriting_ads_y_hooks(kw, preguntas, intencion="Comercial / Transaccional", pais="Colombia")
    
    print("\n[Google Ads Titulos (Max 30 car)]:")
    for t in res["google_ads"]["titulos"]:
        print(f"  - '{t}' ({len(t)} car)")
        assert len(t) <= 35, f"Título excede límite: {t}"

    print("\n[Google Ads Descripciones (Max 90 car)]:")
    for d in res["google_ads"]["descripciones"]:
        print(f"  - '{d}' ({len(d)} car)")
        assert len(d) <= 95, f"Descripción excede límite: {d}"

    print(f"\n[Social Ad Hook]: {res['social_ads']['hook_scroll_stopper'].encode('ascii', 'replace').decode('ascii')}")
    print(f"[TikTok Hooks (Total {len(res['tiktok_reels_hooks'])})]:")
    for h in res["tiktok_reels_hooks"]:
        print(f"  - {h.encode('ascii', 'replace').decode('ascii')}")

    print(f"\n[Guion 30s Video]: {len(res['guion_video_30s'])} bloques")
    assert len(res["google_ads"]["titulos"]) == 5, "Deben haber 5 títulos de Google Ads"
    assert len(res["google_ads"]["descripciones"]) == 3, "Deben haber 3 descripciones de Google Ads"
    assert len(res["tiktok_reels_hooks"]) == 5, "Deben haber 5 hooks de TikTok"
    
    print("\n>>> TEST DE ADS COPYWRITING Y HOOKS EXITOSO <<<")



if __name__ == "__main__":
    test_ads_copywriting()
