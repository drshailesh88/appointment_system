"""
Custom SQLAlchemy types for cross-database compatibility.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.types import TypeDecorator


class JSONB(TypeDecorator):
    """
    JSON type that uses JSONB for PostgreSQL and JSON for other databases.

    This allows models to use JSONB syntax while remaining compatible with SQLite for testing.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        else:
            return dialect.type_descriptor(JSON())
