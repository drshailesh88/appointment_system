"""
Doctor model for practice management.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, generate_uuid, get_utc_now

if TYPE_CHECKING:
    from src.models.appointment import Appointment


class Doctor(Base):
    """
    Doctor entity for the practice.

    Attributes:
        id: Unique identifier (UUID)
        name: Doctor's full name
        specialization: Medical specialization
        qualification: Degrees and qualifications
        registration_number: Medical council registration
        phone: Contact number
        email: Email address
        consultation_fee: Default fee for consultation
        slot_duration: Default appointment duration in minutes
        working_hours: JSON defining working schedule
        created_at: Record creation timestamp
    """

    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Professional Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Practice Settings
    consultation_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("500.00")
    )
    slot_duration: Mapped[int] = mapped_column(Integer, default=15)  # minutes

    # Working Hours - JSON format:
    # {
    #   "monday": {"start": "09:00", "end": "17:00", "break_start": "13:00", "break_end": "14:00"},
    #   "tuesday": {...},
    #   ...
    # }
    working_hours: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Bio/Description
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )

    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="doctor", lazy="dynamic"
    )

    def get_working_hours_for_day(self, day: str) -> Optional[dict[str, str]]:
        """
        Get working hours for a specific day.

        Args:
            day: Day of week (lowercase, e.g., 'monday')

        Returns:
            Dict with start, end, break_start, break_end times or None
        """
        if not self.working_hours:
            return None
        return self.working_hours.get(day.lower())

    def is_available_at(self, day: str, time_str: str) -> bool:
        """
        Check if doctor is available at a specific day and time.

        Args:
            day: Day of week (lowercase)
            time_str: Time in HH:MM format

        Returns:
            True if available, False otherwise
        """
        hours = self.get_working_hours_for_day(day)
        if not hours:
            return False

        start = hours.get("start", "00:00")
        end = hours.get("end", "23:59")
        break_start = hours.get("break_start")
        break_end = hours.get("break_end")

        # Check if within working hours
        if not (start <= time_str <= end):
            return False

        # Check if during break
        if break_start and break_end:
            if break_start <= time_str < break_end:
                return False

        return True

    def __repr__(self) -> str:
        return f"<Doctor(id={self.id}, name={self.name}, specialization={self.specialization})>"
