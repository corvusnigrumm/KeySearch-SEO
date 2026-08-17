"""
Test de integración de rutas FastAPI para el Estudio Editorial y Tags Reales.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from fastapi_app import app


def test_fastapi_editorial_routes():
    client = TestClient(app, follow_redirects=False)

    print("\n1. Testeando ruta GET /editorial...")
    res = client.get("/editorial")
    # Redirige a /login si no autenticado (comportamiento esperado con auth) o responde 200
    assert res.status_code in [200, 307], f"Código inesperado en /editorial: {res.status_code}"
    print(f"GET /editorial responde: {res.status_code} OK")

    print("\n2. Testeando endpoint POST /api/editorial/tags-reales sin auth o con token...")
    # Verificar que el endpoint está registrado
    res_tags = client.post("/api/editorial/tags-reales", json={"keyword": "nevera consume mucha luz"})
    assert res_tags.status_code in [200, 307, 401], f"Código inesperado: {res_tags.status_code}"
    print(f"POST /api/editorial/tags-reales responde: {res_tags.status_code} OK")

    print("\n>>> TODOS LOS TESTS DE RUTAS FASTAPI PASARON EXITOSAMENTE <<<")


if __name__ == "__main__":
    test_fastapi_editorial_routes()
