"""
Tests para scraper/http_cache.py: limpieza automática de cache expirado.
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.http_cache import make_key, get_text, set_text, cleanup_expired, _CLEANUP_DONE


class TestCleanupExpired:
    def setup_method(self):
        import scraper.http_cache as mod
        mod._CLEANUP_DONE = False

    def test_limpia_archivos_expirados(self, cache_dir):
        import scraper.http_cache as mod
        mod._CLEANUP_DONE = False

        key = make_key("https://example.com/expired")
        path = os.path.join(cache_dir, f"{key}.json")
        old_payload = {"ts": int(time.time()) - 999999, "status": 200, "text": "old"}
        with open(path, "w") as f:
            json.dump(old_payload, f)

        removed = cleanup_expired(cache_dir, ttl_seconds=3600)
        assert removed == 1
        assert not os.path.exists(path)

    def test_no_limpia_archivos_vigentes(self, cache_dir):
        import scraper.http_cache as mod
        mod._CLEANUP_DONE = False

        key = make_key("https://example.com/fresh")
        set_text(cache_dir, key, "fresh content", status=200)

        removed = cleanup_expired(cache_dir, ttl_seconds=3600)
        assert removed == 0
        assert os.path.exists(os.path.join(cache_dir, f"{key}.json"))

    def test_cache_dir_inexistente(self):
        removed = cleanup_expired("/nonexistent/path", ttl_seconds=3600)
        assert removed == 0

    def test_cache_dir_none(self):
        removed = cleanup_expired(None, ttl_seconds=3600)
        assert removed == 0

    def test_solo_ejecuta_una_vez(self, cache_dir):
        import scraper.http_cache as mod
        mod._CLEANUP_DONE = False

        key = make_key("https://example.com/once")
        path = os.path.join(cache_dir, f"{key}.json")
        old_payload = {"ts": int(time.time()) - 999999, "status": 200, "text": "old"}
        with open(path, "w") as f:
            json.dump(old_payload, f)

        removed1 = cleanup_expired(cache_dir, ttl_seconds=3600)
        assert removed1 == 1

        removed2 = cleanup_expired(cache_dir, ttl_seconds=3600)
        assert removed2 == 0


class TestHttpCacheIntegracion:
    def test_get_text_limpia_y_devuelve_none(self, cache_dir):
        """cleanup se ejecuta en get_text y limpia expirados."""
        import scraper.http_cache as mod
        mod._CLEANUP_DONE = False

        expired_key = make_key("https://example.com/exp")
        old_payload = {"ts": int(time.time()) - 999999, "status": 200, "text": "expired"}
        with open(os.path.join(cache_dir, f"{expired_key}.json"), "w") as f:
            json.dump(old_payload, f)

        fresh_key = make_key("https://example.com/fresh")
        set_text(cache_dir, fresh_key, "fresh", status=200)

        result = get_text(cache_dir, fresh_key, ttl_seconds=3600)
        assert result == "fresh"
        assert not os.path.exists(os.path.join(cache_dir, f"{expired_key}.json"))
