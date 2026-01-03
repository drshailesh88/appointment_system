"""
SQLAlchemy base configuration and database utilities.
"""

from datetime import datetime
from typing import Generator
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.utils.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


def get_engine(db_path: str | None = None):
    """
    Create and configure SQLAlchemy engine.

    Args:
        db_path: Path to SQLite database. Uses settings if not provided.

    Returns:
        SQLAlchemy Engine instance.
    """
    if db_path is None:
        settings = get_settings()
        db_path = str(settings.database_path)

    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


_session_factory: sessionmaker | None = None


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session.

    Yields:
        SQLAlchemy Session instance.
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine=None) -> None:
    """
    Initialize the database by creating all tables.

    Args:
        engine: SQLAlchemy engine. Creates new one if not provided.
    """
    if engine is None:
        engine = get_engine()

    # Import all models to ensure they're registered
    from src.models import appointment, audit, doctor, invoice, notification, patient, payment, service, staff  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()
