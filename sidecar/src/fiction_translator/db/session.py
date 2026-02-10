"""Database engine and session management."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base


def get_db_path() -> str:
    """Get the database file path."""
    # Default to ~/.fiction-translator/data.db
    data_dir = Path.home() / ".fiction-translator"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "data.db")


_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_path = os.environ.get("FT_DATABASE_PATH", get_db_path())
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


def get_db() -> Session:
    """Get a new database session."""
    factory = get_session_factory()
    return factory()


def init_db():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
