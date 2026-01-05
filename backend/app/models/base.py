"""
Base model with common fields.
"""

import os
import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, func
from sqlalchemy.dialects.postgresql import JSONB as PostgreSQLJSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


# Create a compatibility JSONB type that works with both SQLite and PostgreSQL
class JSONB(TypeDecorator):
    """
    JSONB type that falls back to JSON for SQLite.

    In production (PostgreSQL), uses JSONB for better performance.
    In testing (SQLite), uses JSON for compatibility.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQLJSONB())
        else:
            return dialect.type_descriptor(JSON())


def get_json_type():
    """Get appropriate JSON type based on database."""
    # Always return our compatibility JSONB type
    return JSONB


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
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps."""

    __abstract__ = True
