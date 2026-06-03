import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Determinar la URL de la base de datos
# En Render, se puede configurar DATABASE_URL (ej: postgresql://user:pass@host/db)
# Si no existe, usamos SQLite local.
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Usar SQLite
    # Crear carpeta data si no existe
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    db_path = os.path.join(DATA_DIR, "keysearch.db")
    DATABASE_URL = f"sqlite:///{db_path}"

# SQLAlchemy Engine
# Para SQLite, 'check_same_thread' debe ser False para evitar problemas con FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relacion (Un usuario tiene muchas busquedas)
    searches = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    keyword = Column(String(200), nullable=False)
    country = Column(String(10), nullable=False)
    profile = Column(String(50), nullable=False)
    json_data = Column(Text, nullable=False)  # Se guardara como string JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="searches")


def init_db():
    """Crea las tablas en la base de datos."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Generador para obtener la sesion de la base de datos por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
