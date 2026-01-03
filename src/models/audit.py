"""
Audit log model for tracking all changes.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, generate_uuid, get_utc_now


class AuditLog(Base):
    """
    Audit log entity for compliance and debugging.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Staff member who made the change
        action: Type of action (create, update, delete, etc.)
        entity_type: Type of entity modified
        entity_id: ID of modified entity
        old_values: Previous values (JSON)
        new_values: New values (JSON)
        ip_address: Client IP address
        user_agent: Client user agent
        created_at: When action occurred
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Actor
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Action Details
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Change Details
    old_values: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Client Info
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False, index=True
    )

    @property
    def changes(self) -> dict[str, tuple[Any, Any]]:
        """
        Get dict of changed fields with old and new values.

        Returns:
            Dict mapping field names to (old_value, new_value) tuples
        """
        if not self.old_values or not self.new_values:
            return {}

        changes = {}
        all_keys = set(self.old_values.keys()) | set(self.new_values.keys())

        for key in all_keys:
            old_val = self.old_values.get(key)
            new_val = self.new_values.get(key)
            if old_val != new_val:
                changes[key] = (old_val, new_val)

        return changes

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, "
            f"action={self.action}, "
            f"entity={self.entity_type}:{self.entity_id})>"
        )
