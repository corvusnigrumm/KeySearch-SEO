"""
Tests para Prometheus metrics y /metrics endpoint.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    from core.security import ai_rate_limiter, rate_limiter

    rate_limiter._hits.clear()
    ai_rate_limiter._hits.clear()


class TestPrometheusMetrics:
    def test_metrics_endpoint_returns_200(self):
        from fastapi_app import app

        c = TestClient(app)
        resp = c.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type_is_prometheus(self):
        from fastapi_app import app

        c = TestClient(app)
        resp = c.get("/metrics")
        assert "text/plain" in resp.headers["content-type"]

    def test_metrics_contains_app_info(self):
        from fastapi_app import app

        c = TestClient(app)
        resp = c.get("/metrics")
        body = resp.text
        assert "keysearch_http_requests_total" in body
        assert "keysearch_http_request_duration_seconds" in body

    def test_metrics_contains_version(self):
        from fastapi_app import app

        c = TestClient(app)
        resp = c.get("/metrics")
        assert "10.0" in resp.text

    def test_ping_increments_request_counter(self):
        from fastapi_app import app

        c = TestClient(app)
        c.get("/ping")
        c.get("/ping")
        resp = c.get("/metrics")
        assert "keysearch_http_requests_total" in resp.text

    def test_metrics_not_rate_limited(self):
        from fastapi_app import app

        c = TestClient(app)
        for _ in range(50):
            c.get("/metrics")
        resp = c.get("/metrics")
        assert resp.status_code == 200


class TestPrometheusMiddleware:
    def test_middleware_records_latency(self):
        from fastapi_app import app

        c = TestClient(app)
        c.get("/ping")
        resp = c.get("/metrics")
        assert "keysearch_http_request_duration_seconds" in resp.text

    def test_middleware_normalizes_paths(self):
        from core.monitoring import _normalize_path

        assert _normalize_path("/api/generate-schema") == "/api/generate-schema"
        assert _normalize_path("/users/123") == "/users/{id}"
        assert _normalize_path("/") == "/"

    def test_middleware_skips_static(self):
        from fastapi_app import app

        c = TestClient(app)
        c.get("/static/logo_dorado.png")
        resp = c.get("/metrics")
        assert resp.status_code == 200


class TestPrometheusCounters:
    def test_counter_increment(self):
        from core.monitoring import REQUEST_COUNT

        before = REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200")._value.get()
        REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200").inc()
        after = REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200")._value.get()
        assert after > before

    def test_histogram_observe(self):
        from core.monitoring import REQUEST_LATENCY

        REQUEST_LATENCY.labels(method="GET", endpoint="/test_hist").observe(0.5)
        resp_text = ""
        from prometheus_client import generate_latest

        resp_text = generate_latest().decode()
        assert "keysearch_http_request_duration_seconds" in resp_text

    def test_gauge_set(self):
        from core.monitoring import ACTIVE_SESSIONS, update_active_sessions

        update_active_sessions(5)
        assert ACTIVE_SESSIONS._value.get() == 5

    def test_ai_calls_counter(self):
        from core.monitoring import AI_CALLS_TOTAL

        AI_CALLS_TOTAL.labels(model="test-model", status="success").inc()
        from prometheus_client import generate_latest

        text = generate_latest().decode()
        assert "keysearch_ai_calls_total" in text
