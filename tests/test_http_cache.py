import os
import json
import tempfile
import time
import unittest

from scraper.http_cache import get_text, make_key, set_text


class HttpCacheTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = make_key("https://example.com/test")
            set_text(tmp, key, "hola", status=200)
            self.assertEqual(get_text(tmp, key, ttl_seconds=3600), "hola")

    def test_ttl_expira(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = make_key("https://example.com/ttl")
            set_text(tmp, key, "x", status=200)
            path = os.path.join(tmp, f"{key}.json")
            with open(path, "r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
            payload["ts"] = 1
            with open(path, "w", encoding="utf-8") as file_handle:
                json.dump(payload, file_handle, ensure_ascii=False)
            self.assertIsNone(get_text(tmp, key, ttl_seconds=1))


if __name__ == "__main__":
    unittest.main()
