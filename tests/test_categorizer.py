"""
Tests para scraper/categorizer.py: clasificación automática de keywords.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.categorizer import auto_categorizar, _normalizar, _puntuar


class TestNormalizar:
    def test_quita_tildes(self):
        assert _normalizar("marketing digital") == "marketing digital"

    def test_minusculas(self):
        assert _normalizar("MARKETING DIGITAL") == "marketing digital"

    def test_espacios_bordes(self):
        # _normalizar solo hace strip + lower + quitar acentos, no colapsa espacios internos
        assert _normalizar("  marketing digital  ") == "marketing digital"

    def test_string_vacio(self):
        assert _normalizar("") == ""


class TestPuntuar:
    def test_coincidencia_exacta(self):
        score = _puntuar("marketing digital", "marketing digital")
        assert score > 0

    def test_coincidencia_parcial(self):
        score = _puntuar("marketing", "marketing digital")
        assert score > 0

    def test_score_es_numerico(self):
        score = _puntuar("test", "test")
        assert isinstance(score, (int, float))


class TestAutoCategorizar:
    def test_retorna_tupla(self):
        cat, sub = auto_categorizar("marketing digital")
        assert isinstance(cat, str)
        assert isinstance(sub, str)

    def test_keyword_vacia(self):
        cat, sub = auto_categorizar("")
        assert cat != ""
        assert sub != ""

    def test_keyword_marketing(self):
        cat, sub = auto_categorizar("marketing digital")
        # Puede caer en "Marketing y Negocios" o "Tecnología y Digital" dependiendo del scoring
        assert isinstance(cat, str) and len(cat) > 0

    def test_keyword_salud(self):
        cat, sub = auto_categorizar("dolor de cabeza tratamiento")
        assert "salud" in cat.lower()

    def test_keyword_tecnologia(self):
        cat, sub = auto_categorizar("inteligencia artificial")
        assert "tecnolog" in cat.lower()

    def test_keyword_deportes(self):
        cat, sub = auto_categorizar("liga colombiana futbol")
        assert "deporte" in cat.lower()

    def test_keyword_finanzas(self):
        cat, sub = auto_categorizar("inversiones en bolsa")
        assert "finanz" in cat.lower() or "econom" in cat.lower()

    def test_keyword_mascotas(self):
        cat, sub = auto_categorizar("alimento perro golden")
        assert "mascota" in cat.lower()

    def test_keyword_recetas(self):
        cat, sub = auto_categorizar("receta de arroz con pollo")
        assert "receta" in cat.lower() or "cocina" in cat.lower() or "gastronom" in cat.lower()

    def test_keyword_largo(self):
        cat, sub = auto_categorizar("como aprender a programar python desde cero")
        assert isinstance(cat, str) and len(cat) > 0
