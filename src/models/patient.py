"""
Patient model - synced with DocAssist EMR.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, generate_uuid, get_utc_now

if TYPE_CHECKING:
    from src.models.appointment import Appointment
    from src.models.invoice import Invoice


class Patient(Base):
    """
    Patient entity - core record synced with EMR.

    Attributes:
        id: Unique identifier (UUID)
        emr_id: Corresponding ID in EMR system for sync
        first_name: Patient's first name
        last_name: Patient's last name (optional)
        phone: Primary contact number (required)
        email: Email address (optional)
        date_of_birth: Birth date for age calculation
        gender: M/F/O
        address: Street address
        city: City name
        pincode: Postal code
        aadhaar_hash: Hashed Aadhaar number for verification
        photo_path: Path to patient photo
        is_active: Soft delete flag
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
        synced_at: Last EMR sync timestamp
    """

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    emr_id: Mapped[Optional[str]] = mapped_column(String(36), unique=True, nullable=True)

    # Personal Information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)  # M/F/O

    # Address
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Verification
    aadhaar_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False
    )
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="patient", lazy="dynamic"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", back_populates="patient", lazy="dynamic"
    )

    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def age(self) -> Optional[int]:
        """Calculate patient's age from date of birth."""
        if not self.date_of_birth:
            return None
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, name={self.full_name}, phone={self.phone})>"
