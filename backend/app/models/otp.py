"""
OTP model for patient authentication.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, UUID


class OTP(BaseModel):
    """
    OTP model for patient phone verification.

    Attributes:
        phone: Phone number for OTP
        otp_code: 6-digit OTP code
        expires_at: Expiration timestamp
        is_verified: Whether OTP has been verified
        attempts: Number of verification attempts
    """

    __tablename__ = "otps"

    phone: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    otp_code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(default=0)

    # Optional patient reference after first booking
    patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(), nullable=True)

    def is_valid(self) -> bool:
        """Check if OTP is still valid."""
        return (
            not self.is_verified
            and self.attempts < 3
            and datetime.now(timezone.utc) < self.expires_at
        )

    def __repr__(self) -> str:
        return f"<OTP {self.phone} expires={self.expires_at}>"
