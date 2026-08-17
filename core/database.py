import datetime
import logging
import os
from collections.abc import Generator

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

logger = logging.getLogger("keysearch.db")

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)

    db_path = os.path.join(DATA_DIR, "keysearch.db")
    DATABASE_URL = f"sqlite:///{db_path}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

_pool_kwargs = {}
if not DATABASE_URL.startswith("sqlite"):
    _pool_kwargs = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

engine = create_engine(DATABASE_URL, connect_args=connect_args, **_pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    searches = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("PipelineSession", back_populates="user", cascade="all, delete-orphan")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    keyword = Column(String(200), nullable=False)
    country = Column(String(10), nullable=False)
    profile = Column(String(50), nullable=False)
    json_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="searches")


class PipelineSession(Base):
    __tablename__ = "pipeline_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_running = Column(Boolean, default=False)
    progress = Column(Integer, default=0)
    status_msg = Column(String(500), default="Listo.")
    error_msg = Column(Text, nullable=True)
    country = Column(String(10), default="co")
    profile = Column(String(50), default="normal")
    keywords_json = Column(Text, default="[]")
    last_run_data_json = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="sessions")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Session TTL Cleanup ──────────────────────────────────────────────────────
SESSION_TTL_HOURS = 24 * 7  # 7 dias


def cleanup_expired_sessions(max_age_hours: int = SESSION_TTL_HOURS) -> int:
    """Elimina sesiones PipelineSession mas antiguas que max_age_hours."""
    db = SessionLocal()
    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=max_age_hours)
        expired = db.query(PipelineSession).filter(PipelineSession.created_at < cutoff).all()
        count = len(expired)
        for s in expired:
            db.delete(s)
        db.commit()
        if count > 0:
            logger.info("Session TTL cleanup: %d sesiones expiradas eliminadas", count)
        return count
    except Exception as e:
        db.rollback()
        logger.error("Error en session cleanup: %s", e)
        return 0
    finally:
        db.close()


# ── Concurrency Limits ───────────────────────────────────────────────────────
import threading

_active_pipelines: int = 0
_pipeline_lock = threading.Lock()
MAX_CONCURRENT_PIPELINES = 3


def acquire_pipeline_slot() -> bool:
    global _active_pipelines
    with _pipeline_lock:
        if _active_pipelines < MAX_CONCURRENT_PIPELINES:
            _active_pipelines += 1
            return True
        return False


def release_pipeline_slot() -> None:
    global _active_pipelines
    with _pipeline_lock:
        if _active_pipelines > 0:
            _active_pipelines -= 1


def get_active_pipeline_count() -> int:
    with _pipeline_lock:
        return _active_pipelines
