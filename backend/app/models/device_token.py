"""
Device Token model for push notifications.

Stores FCM device tokens for registered users to enable push notifications.
"""

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class DevicePlatform(str, Enum):
    """Mobile platform types."""

    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class DeviceToken(BaseModel):
    """
    FCM Device Token for push notifications.

    Stores device registration tokens to send push notifications.
    A user can have multiple devices registered.

    Attributes:
        user_id: Associated user
        device_token: FCM registration token (unique)
        platform: Device platform (ios/android/web)
        device_name: Optional device name/model
        is_active: Whether this token is still valid
        last_used_at: Last time a notification was sent to this token
    """

    __tablename__ = "device_tokens"

    # User Association
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FCM Token
    device_token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
    )

    # Device Info
    platform: Mapped[str] = mapped_column(
        String(20),
        default=DevicePlatform.ANDROID.value,
        nullable=False,
    )
    device_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="device_tokens")

    # Unique constraint: one token per user-device combination
    __table_args__ = (
        UniqueConstraint("user_id", "device_token", name="unique_user_device_token"),
    )

    def __repr__(self) -> str:
        return f"<DeviceToken {self.platform} for user {self.user_id}>"

    def deactivate(self) -> None:
        """Mark this token as inactive (e.g., after FCM error)."""
        self.is_active = False
