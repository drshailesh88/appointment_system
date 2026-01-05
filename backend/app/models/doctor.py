"""
Doctor model for medical professionals.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.types import JSONB

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.clinic import Clinic
    from app.models.lab_result import LabOrder


class Doctor(BaseModel):
    """
    Doctor model for medical professionals.

    Attributes:
        name: Full name with title (Dr. Priya Patel)
        specialization: Medical specialization
        qualification: Degrees (MBBS, MD, etc.)
        registration_number: Medical council registration
        clinic_id: Associated clinic
        consultation_fee: Default consultation fee
        slot_duration: Default appointment duration in minutes
        working_hours: JSON defining weekly schedule
        is_active: Whether doctor is accepting appointments
    """

    __tablename__ = "doctors"

    # Professional Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(500), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Clinic Association
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )

    # Practice Settings
    consultation_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("500.00"),
    )
    followup_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    slot_duration: Mapped[int] = mapped_column(Integer, default=15)  # minutes

    # Working Hours - JSON format:
    # {
    #   "monday": [{"start": "09:00", "end": "13:00"}, {"start": "17:00", "end": "20:00"}],
    #   "tuesday": [...],
    #   "sunday": null  // Off day
    # }
    working_hours: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Break slots - for lunch, etc.
    break_slots: Mapped[list[dict[str, str]] | None] = mapped_column(JSONB, nullable=True)

    # Profile
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    languages: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    accepting_new_patients: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="doctors")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="doctor",
    )
    lab_orders: Mapped[list["LabOrder"]] = relationship(
        "LabOrder",
        back_populates="doctor",
    )

    def __repr__(self) -> str:
        return f"<Doctor {self.name} ({self.specialization})>"
