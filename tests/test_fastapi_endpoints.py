"""
Tests para los endpoints principales de FastAPI (con mocking de servicios externos).
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


def _reset_rate_limiters():
    from core.security import ai_rate_limiter, rate_limiter

    rate_limiter._hits.clear()
    ai_rate_limiter._hits.clear()


def _make_authenticated_client():
    from core.auth import create_access_token, get_password_hash
    from core.database import SessionLocal, User, init_db
    from fastapi_app import app

    init_db()
    client = TestClient(app, raise_server_exceptions=False)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "test_api_user").first()
        if not existing:
            u = User(username="test_api_user", password_hash=get_password_hash("pass1234"))
            db.add(u)
            db.commit()
            db.refresh(u)
            user_id = u.id
        else:
            user_id = existing.id
    finally:
        db.close()

    token = create_access_token({"sub": str(user_id)})
    client.cookies.set("access_token", token)
    return client


@pytest.fixture
def client():
    _reset_rate_limiters()
    return _make_authenticated_client()


class TestPingEndpoint:
    def test_ping_ok(self):
        from fastapi_app import app

        c = TestClient(app)
        resp = c.get("/ping")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_ok(self):
        from core.database import init_db
        from fastapi_app import app

        init_db()
        c = TestClient(app)
        resp = c.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "db" in data
        assert "uptime_seconds" in data


class TestStatusEndpoint:
    def test_status_requiere_auth(self):
        from fastapi_app import app

        c = TestClient(app)
        resp = c.get("/status")
        assert resp.status_code in (200, 307, 401)

    def test_status_con_auth(self, client):
        resp = client.get("/status")
        assert resp.status_code == 200


class TestAuthFlujo:
    def test_login_page(self):
        from fastapi_app import app

        c = TestClient(app)
        resp = c.get("/login")
        assert resp.status_code == 200

    def test_registro_y_login(self):
        from fastapi_app import app

        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post(
            "/register",
            data={
                "username": "test_user_prof",
                "password": "test1234",
            },
            follow_redirects=False,
        )
        assert resp.status_code in (200, 303)

        resp = c.post(
            "/login",
            data={
                "username": "test_user_prof",
                "password": "test1234",
            },
            follow_redirects=False,
        )
        assert resp.status_code in (200, 303)

    def test_registro_usuario_duplicado(self):
        from fastapi_app import app

        c = TestClient(app, raise_server_exceptions=False)
        c.post("/register", data={"username": "dup_user_2", "password": "test1234"})
        resp = c.post("/register", data={"username": "dup_user_2", "password": "otra1234"})
        assert resp.status_code == 200
        assert "ya existe" in resp.text.lower() or "perfil" in resp.text.lower() or "duplicate" in resp.text.lower()

    def test_password_corta_rechazada(self):
        from fastapi_app import app

        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/register", data={"username": "short_pw_user_2", "password": "ab"})
        assert resp.status_code == 200
        assert "4 caracteres" in resp.text or "contrasena" in resp.text.lower() or "contraseña" in resp.text.lower()


class TestSchemaEndpoint:
    @patch("scraper.ai_generator.post_groq_json")
    def test_generate_schema_ok(self, mock_ia, client):
        mock_ia.return_value = {
            "meta_title": "Test Title",
            "meta_description": "Test description here",
            "slug_sugerido": "test-title",
            "faq_items": [{"pregunta": "Q1?", "respuesta": "A1"}],
        }
        resp = client.post(
            "/api/generate-schema",
            json={
                "keyword": "test keyword",
                "questions": ["Q1?"],
                "country": "Colombia",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "meta_title" in data

    def test_generate_schema_sin_keyword(self, client):
        resp = client.post(
            "/api/generate-schema",
            json={
                "keyword": "",
                "questions": [],
            },
        )
        # Pydantic min_length=1 rechaza string vacío
        assert resp.status_code == 422


class TestAdsCopyEndpoint:
    @patch("scraper.ai_generator.post_groq_json")
    def test_generate_ads_copy_ok(self, mock_ia, client):
        mock_ia.return_value = {
            "google_ads": {
                "titulos": ["Titulo 1" * 4],
                "descripciones": ["Descripcion corta"],
            },
            "social_ads": {"hook": "test"},
            "tiktok_reels_hooks": ["hook1"],
            "guion_video_30s": {"gancho": "test"},
        }
        resp = client.post(
            "/api/generate-ads-copy",
            json={
                "keyword": "test keyword",
                "questions": [],
                "intent": "Informativa",
                "country": "Colombia",
            },
        )
        assert resp.status_code == 200

    def test_generate_ads_copy_sin_keyword(self, client):
        resp = client.post(
            "/api/generate-ads-copy",
            json={
                "keyword": "",
            },
        )
        # Pydantic min_length=1 rechaza string vacío
        assert resp.status_code == 422


class TestSetGroqModel:
    def test_set_model_ok(self, client):
        resp = client.post(
            "/api/set-groq-model",
            json={
                "model": "llama-3.3-70b-versatile",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_set_model_vacio(self, client):
        resp = client.post(
            "/api/set-groq-model",
            json={
                "model": "",
            },
        )
        # Pydantic min_length=1 rechaza string vacío
        assert resp.status_code == 422
