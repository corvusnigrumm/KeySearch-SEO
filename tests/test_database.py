"""
Tests para core/database.py: session TTL cleanup y concurrency limits.
"""
import sys
import os
import datetime
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    SessionLocal, PipelineSession, init_db,
    cleanup_expired_sessions, SESSION_TTL_HOURS,
    acquire_pipeline_slot, release_pipeline_slot, get_active_pipeline_count,
    MAX_CONCURRENT_PIPELINES,
)


class TestSessionTTL:
    def setup_method(self):
        init_db()

    def test_cleanup_returns_int(self):
        result = cleanup_expired_sessions()
        assert isinstance(result, int)

    def test_cleanup_removes_old_sessions(self):
        db = SessionLocal()
        try:
            old = PipelineSession(
                session_id="old_session_ttl_test",
                created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=999),
            )
            db.add(old)
            db.commit()
        finally:
            db.close()

        removed = cleanup_expired_sessions()
        assert removed >= 1

    def test_cleanup_keeps_recent_sessions(self):
        db = SessionLocal()
        try:
            recent = PipelineSession(session_id="recent_session_ttl_test")
            db.add(recent)
            db.commit()
            recent_id = recent.id
        finally:
            db.close()

        removed = cleanup_expired_sessions()
        db = SessionLocal()
        try:
            remaining = db.query(PipelineSession).filter(PipelineSession.id == recent_id).first()
            assert remaining is not None
            db.delete(remaining)
            db.commit()
        finally:
            db.close()

    def test_ttl_default_is_7_days(self):
        assert SESSION_TTL_HOURS == 24 * 7


class TestConcurrencyLimits:
    def setup_method(self):
        from core.database import _pipeline_lock, _active_pipelines
        import core.database as mod
        with _pipeline_lock:
            mod._active_pipelines = 0

    def test_acquire_when_empty(self):
        assert acquire_pipeline_slot() is True
        assert get_active_pipeline_count() == 1
        release_pipeline_slot()

    def test_release_decrements(self):
        acquire_pipeline_slot()
        assert get_active_pipeline_count() == 1
        release_pipeline_slot()
        assert get_active_pipeline_count() == 0

    def test_max_concurrent_limit(self):
        for _ in range(MAX_CONCURRENT_PIPELINES):
            assert acquire_pipeline_slot() is True
        assert get_active_pipeline_count() == MAX_CONCURRENT_PIPELINES
        assert acquire_pipeline_slot() is False
        for _ in range(MAX_CONCURRENT_PIPELINES):
            release_pipeline_slot()
        assert get_active_pipeline_count() == 0

    def test_release_below_zero_prevented(self):
        release_pipeline_slot()
        assert get_active_pipeline_count() == 0
