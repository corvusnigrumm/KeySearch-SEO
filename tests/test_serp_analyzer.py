"""
Test para el Analizador de Debilidades de la SERP y Oportunidades de Oro.
"""
import sys
import os
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.serp_analyzer import analizar_debilidades_serp, _clasificar_tipo_dominio


def test_domain_classification():
    print("--> Testeando Clasificación de Dominios...")
    casos = [
        ("reddit.com", "https://www.reddit.com/r/technology/comments/123", "Foro / UGC"),
        ("quora.com", "https://es.quora.com/Que-es-la-inteligencia-artificial", "Foro / UGC"),
        ("pinterest.com", "https://www.pinterest.com/pin/12345", "Red Social"),
        ("blogspot.com", "https://mitrabajo.blogspot.com/2026/01/ia.html", "Blog Libre / Web 2.0"),
        ("wikipedia.org", "https://es.wikipedia.org/wiki/Inteligencia_artificial", "Alta Autoridad / Oficial"),
        ("elpais.com", "https://elpais.com/tecnologia/2026-08-14/articulo.html", "Portal / Editorial"),
    ]
    for dom, url, expected_type in casos:
        tipo, badge, icon = _clasificar_tipo_dominio(dom, url)
        print(f"  - {dom} -> Tipo: {tipo} (Esperado: {expected_type})")
        assert tipo == expected_type, f"Fallo en {dom}: obtenido {tipo}, esperado {expected_type}"

    print("OK Clasificación de Dominios")


def test_serp_weakness_detector():
    print("\n--> Testeando Detección de SERP Weakness...")
    mock_html = """
    <html>
      <body>
        <div class="g">
          <a href="https://www.reddit.com/r/SEO/comments/como_crear_blog">
            <h3 class="LC20lb">¿Cómo crear un blog en 2026? - Reddit</h3>
          </a>
          <div class="VwiC3b">Alguien me puede explicar cómo crear un blog fácil y rápido...</div>
        </div>
        <div class="g">
          <a href="https://es.quora.com/Cual-es-el-mejor-hosting">
            <h3 class="LC20lb">¿Cuál es el mejor hosting barato? - Quora</h3>
          </a>
          <div class="VwiC3b">En mi experiencia los mejores hostings son...</div>
        </div>
        <div class="g">
          <a href="https://www.pinterest.com/pin/ideas-blogs">
            <h3 class="LC20lb">Ideas para crear blogs exitosos en Pinterest</h3>
          </a>
          <div class="VwiC3b">Descubre las mejores ideas de diseño...</div>
        </div>
        <div class="g">
          <a href="https://ejemplo.com/guia-blogs">
            <h3 class="LC20lb">Guía paso a paso para crear un blog</h3>
          </a>
          <div class="VwiC3b">Aprende paso a paso cómo iniciar tu sitio web...</div>
        </div>
      </body>
    </html>
    """
    soup = BeautifulSoup(mock_html, "lxml")
    res = analizar_debilidades_serp(soup, "crear un blog")

    print(f"  - Total competidores detectados: {res['total_analizados']}")
    print(f"  - Puntos de oportunidad: {res['puntos_oportunidad']}")
    print(f"  - Nivel de oportunidad: {res['nivel_oportunidad']}")
    print(f"  - Dificultad estimada: {res['dificultad_estimada']}")
    print(f"  - Es oportunidad de oro: {res['es_oportunidad_oro']}")
    print(f"  - Debilidades encontradas: {len(res['debilidades_detectadas'])}")

    assert res['total_analizados'] >= 4, "No extrajo todos los competidores"
    assert res['es_oportunidad_oro'] == True, "Debería ser Oportunidad de Oro por tener Reddit en #1 y Quora en #2"
    print("\n>>> TEST DE SERP WEAKNESS DETECTOR EXITOSO <<<")



if __name__ == "__main__":
    test_domain_classification()
    test_serp_weakness_detector()
