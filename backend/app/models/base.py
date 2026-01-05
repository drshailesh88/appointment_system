"""
Base model with common fields.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB as PostgresJSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


class UUID(TypeDecorator):
    """
    Database-agnostic UUID type that uses UUID for PostgreSQL and String for SQLite.

    This allows tests to run with SQLite while production uses PostgreSQL UUID.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class JSONB(TypeDecorator):
    """
    Database-agnostic JSON type that uses JSONB for PostgreSQL and JSON for others.

    This allows tests to run with SQLite while production uses PostgreSQL JSONB.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresJSONB())
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps."""

    __abstract__ = True
