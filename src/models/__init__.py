"""
Data models for DocAssist Practice Manager.

All models use SQLAlchemy ORM with Pydantic for validation.
"""

from src.models.base import Base, get_engine, get_session, init_db

__all__ = ["Base", "get_engine", "get_session", "init_db"]
