import unittest

from scraper.utils import dedupe_key, limpiar_texto, slugify


class UtilsTests(unittest.TestCase):
    def test_limpiar_texto_normaliza_espacios(self):
        self.assertEqual(limpiar_texto(" hola   mundo "), "hola mundo")

    def test_limpiar_texto_none(self):
        self.assertEqual(limpiar_texto(""), "")

    def test_slugify_quita_acentos_y_puntuacion(self):
        self.assertEqual(slugify("España: fútbol & más"), "espana_futbol_mas")

    def test_slugify_limita_longitud(self):
        self.assertLessEqual(len(slugify("a" * 500)), 80)

    def test_dedupe_key_normaliza_acentos_y_puntuacion(self):
        self.assertEqual(dedupe_key("¿Qué   es  Perú?"), "que es peru")


if __name__ == "__main__":
    unittest.main()
