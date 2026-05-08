import unittest

from scraper.volume_estimator import _categorizar_prioridad, _score_por_posicion


class VolumeEstimatorTests(unittest.TestCase):
    def test_score_rango(self):
        score = _score_por_posicion(0, 10, 1.0)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_score_decrece_con_posicion(self):
        score_primero = _score_por_posicion(0, 10, 1.0)
        score_ultimo = _score_por_posicion(9, 10, 1.0)
        self.assertGreater(score_primero, score_ultimo)

    def test_categoria_por_umbral(self):
        self.assertEqual(_categorizar_prioridad(80), "Muy alta")
        self.assertEqual(_categorizar_prioridad(55), "Alta")
        self.assertEqual(_categorizar_prioridad(30), "Media")
        self.assertEqual(_categorizar_prioridad(15), "Baja")
        self.assertEqual(_categorizar_prioridad(0), "Muy baja")


if __name__ == "__main__":
    unittest.main()

