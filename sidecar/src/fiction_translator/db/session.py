"""Database engine and session management."""
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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


def upgrade_db():
    """Run pending Alembic migrations."""
    try:
        from alembic.config import Config

        from alembic import command

        # Get the alembic directory path (relative to this file's parent directory)
        # This file is in src/fiction_translator/db/session.py
        # alembic/ is at the sidecar root, which is 3 levels up from src/
        sidecar_root = Path(__file__).parents[3]
        alembic_dir = sidecar_root / "alembic"

        if not alembic_dir.exists():
            # Alembic not set up, fall back to create_all
            return False

        # Create alembic config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(alembic_dir))

        # Get database URL
        db_path = os.environ.get("FT_DATABASE_PATH", get_db_path())
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

        # Suppress alembic output to stderr unless in verbose mode
        if not os.environ.get("FT_VERBOSE"):
            # Redirect alembic logging
            alembic_cfg.set_main_option("sqlalchemy.echo", "false")

        # Run migrations
        command.upgrade(alembic_cfg, "head")
        return True
    except ImportError:
        # Alembic not installed, fall back to create_all
        return False
    except Exception as e:
        # Migration failed, log and fall back
        print(f"Warning: Migration failed: {e}", file=sys.stderr)
        return False


def init_db():
    """Initialize database schema.

    Tries to run Alembic migrations first. If that fails or Alembic
    is not available, falls back to create_all().
    """
    engine = get_engine()

    # Try migrations first
    if upgrade_db():
        return

    # Fallback to create_all if migrations didn't run
    Base.metadata.create_all(bind=engine)
