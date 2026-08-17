"""
Tests para core/auth.py: hashing de passwords y JWT tokens.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    SECRET_KEY,
    ALGORITHM,
)


class TestPasswordHashing:
    def test_hash_genera_bcrypt(self):
        h = get_password_hash("mi_password")
        assert isinstance(h, str)
        assert h.startswith("$2b$"), f"Hash should start with $2b$, got: {h[:10]}"

    def test_mismo_password_genera_distintos_hashes(self):
        h1 = get_password_hash("test123")
        h2 = get_password_hash("test123")
        assert h1 != h2

    def test_verify_password_correcta(self):
        password = "secreta123"
        h = get_password_hash(password)
        assert verify_password(password, h) is True

    def test_verify_password_incorrecta(self):
        h = get_password_hash("correcta")
        assert verify_password("incorrecta", h) is False

    def test_verify_password_hash_malformado(self):
        assert verify_password("test", "invalid_hash_format") is False

    def test_verify_password_hash_vacio(self):
        assert verify_password("test", "") is False

    def test_password_unicode(self):
        h = get_password_hash("contraseña_con_tilde")
        assert verify_password("contraseña_con_tilde", h) is True
        assert verify_password("contrasena_sin_tilde", h) is False


class TestJWT:
    def test_create_and_decode_token(self):
        data = {"sub": "42"}
        token = create_access_token(data)
        assert isinstance(token, str)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_token_contiene_exp(self):
        token = create_access_token({"sub": "1"})
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_token_contiene_iss_aud(self):
        token = create_access_token({"sub": "1"})
        payload = decode_access_token(token)
        assert payload["iss"] == "keysearch"
        assert payload["aud"] == "keysearch"

    def test_token_invalido_devuelve_none(self):
        payload = decode_access_token("token_invalido_completamente")
        assert payload is None

    def test_token_vacio_devuelve_none(self):
        payload = decode_access_token("")
        assert payload is None

    def test_secret_key_no_es_hardcodeada(self):
        assert SECRET_KEY != "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"

    def test_algorithm_es_hs256(self):
        assert ALGORITHM == "HS256"
