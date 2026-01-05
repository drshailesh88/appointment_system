"""
Quick test to verify JSONB compatibility fix works with SQLite.
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.doctor import Doctor
from app.models.types import JSONB


def test_jsonb_with_sqlite():
    """Test that our custom JSONB type works with SQLite."""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")

    # Create tables (this should not raise JSONB errors)
    Base.metadata.create_all(engine)

    print("✓ Tables created successfully with JSONB fields")

    # Cleanup
    Base.metadata.drop_all(engine)


def test_jsonb_dialect_detection():
    """Test that JSONB type correctly detects database dialect."""
    from sqlalchemy.dialects import sqlite, postgresql

    jsonb_type = JSONB()

    # Test with SQLite
    sqlite_impl = jsonb_type.load_dialect_impl(sqlite.dialect())
    print(f"✓ SQLite uses: {type(sqlite_impl).__name__}")

    # Test with PostgreSQL
    pg_impl = jsonb_type.load_dialect_impl(postgresql.dialect())
    print(f"✓ PostgreSQL uses: {type(pg_impl).__name__}")

    assert str(type(sqlite_impl).__name__) == "JSON"
    assert "JSONB" in str(type(pg_impl).__name__)


if __name__ == "__main__":
    print("Testing JSONB compatibility fix...\n")

    test_jsonb_dialect_detection()
    print()
    test_jsonb_with_sqlite()

    print("\n✓ All JSONB compatibility tests passed!")
