"""
Test para el Módulo de Ideación Editorial, Tags Reales de Google Trends y Exportación DOCX.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.editorial_ideator import (
    exportar_nota_docx,
    exportar_nota_html,
    exportar_nota_markdown,
    generar_ideas_notas_angulos,
    obtener_tags_reales_google,
    redactar_nota_editorial,
)


def test_editorial_pipeline():
    kw = "nevera consume mucha luz"
    sugs = [
        "nevera consume mucha luz porque",
        "por que mi nevera consume mucha luz",
        "nevera no enfria y consume mucha luz",
        "como saber si la nevera consume mucha luz",
        "nevera inverter consume menos luz",
        "trucos para ahorrar luz con la nevera",
    ]
    paas = [
        "¿Por qué mi nevera está consumiendo tanta luz?",
        "¿Cómo saber si una nevera gasta mucha energía?",
        "¿Qué electrodoméstico consume más luz en la casa?",
    ]

    print("\n1. Probando extracción de Tags Reales de Google Trends & SERP...")
    tags_info = obtener_tags_reales_google(kw, sugs, paas, pais="Colombia")
    assert isinstance(tags_info, dict), "tags_info no es dict"
    assert "tags_lista_plana" in tags_info, "Falta tags_lista_plana"
    assert len(tags_info["tags_lista_plana"]) > 0, "No se generaron tags planos"
    print(f"Tags extraídos ({len(tags_info['tags_lista_plana'])}): {tags_info['tags_lista_plana'][:5]}...")
    print(f"CSV Tags Ready: {tags_info['tags_csv_ready'][:80]}...")

    print("\n2. Probando Generación de Ideas de Notas por Ángulos...")
    ideas = generar_ideas_notas_angulos(kw, sugs, paas, pais="Colombia", tags_reales=tags_info)
    assert isinstance(ideas, list), "ideas no es lista"
    assert len(ideas) >= 3, "Debe generar al menos 3 ideas de notas"
    for idea in ideas:
        print(f"[{idea.get('angulo')}]: {idea.get('titular_h1')}")
        assert "titular_h1" in idea, "Falta titular_h1 en idea"
        assert "bajada" in idea, "Falta bajada en idea"

    print("\n3. Probando Redacción de Nota Estructurada según Manual de Estilo...")
    primera_idea = ideas[0]
    nota = redactar_nota_editorial(
        keyword_base=kw,
        angulo=primera_idea.get("angulo", "Tecnología, Ahorro y Configuración"),
        titular_h1=primera_idea.get("titular_h1"),
        sugerencias=sugs,
        preguntas_paa=paas,
        pais="Colombia",
        tags_reales=tags_info,
    )
    assert isinstance(nota, dict), "nota no es dict"
    assert "titular_h1" in nota, "Falta titular_h1 en nota redactada"
    assert "bajada" in nota, "Falta bajada en nota redactada"
    assert "secciones_h2" in nota and len(nota["secciones_h2"]) > 0, "Faltan secciones H2"
    assert "tags_reales" in nota and len(nota["tags_reales"]) > 0, "Faltan tags reales en nota"
    print(f"\nNota H1: {nota['titular_h1']}")
    print(f"Bajada: {nota['bajada']}")
    print(f"Interlink: {nota.get('interlink_sugerido')}")
    print(f"Total H2s: {len(nota['secciones_h2'])}")

    print("\n4. Probando Exportación Markdown y HTML...")
    md = exportar_nota_markdown(nota)
    html = exportar_nota_html(nota)
    assert len(md) > 200, "Markdown generado muy corto"
    assert "<h1>" in html, "HTML le falta etiqueta h1"
    print("Markdown y HTML generados correctamente.")

    print("\n5. Probando Exportación Word (.docx)...")
    test_docx_path = "test_nota_editorial.docx"
    buf = exportar_nota_docx(nota, filepath=test_docx_path)
    assert os.path.exists(test_docx_path), "No se creó el archivo test_nota_editorial.docx"
    assert os.path.getsize(test_docx_path) > 1000, "Archivo docx generado está vacío o corrupto"
    print(f"Archivo DOCX generado exitosamente ({os.path.getsize(test_docx_path)} bytes).")
    if os.path.exists(test_docx_path):
        os.remove(test_docx_path)

    print("\n>>> TODOS LOS TESTS DEL ESTUDIO EDITORIAL PASARON EXITOSAMENTE <<<")


if __name__ == "__main__":
    test_editorial_pipeline()
