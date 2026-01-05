"""
Patient model for patient management.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, UUID

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.clinic import Clinic
    from app.models.document import Document
    from app.models.insurance import PatientInsurance
    from app.models.invoice import Invoice
    from app.models.phone_call import PhoneCall
    from app.models.procedure import Procedure


class Patient(BaseModel):
    """
    Patient model for patient records.

    Attributes:
        first_name: Patient's first name
        last_name: Patient's last name
        phone: Primary contact (required, used for SMS/WhatsApp)
        email: Email address (optional)
        date_of_birth: For age calculation
        gender: M/F/O
        clinic_id: Associated clinic
        emr_patient_id: Link to EMR system for sync
    """

    __tablename__ = "patients"

    # Personal Information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(1), nullable=True)  # M/F/O

    # Address
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Verification
    aadhaar_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Clinic Association
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )

    # EMR Integration
    emr_patient_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    emr_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Medical Info (basic, detailed in EMR)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Preferences
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    sms_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_consent: Mapped[bool] = mapped_column(Boolean, default=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="patients")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="patient",
    )
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="patient")
    procedures: Mapped[list["Procedure"]] = relationship(
        "Procedure",
        back_populates="patient",
    )
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="patient")
    insurances: Mapped[list["PatientInsurance"]] = relationship(
        "PatientInsurance",
        back_populates="patient",
    )
    phone_calls: Mapped[list["PhoneCall"]] = relationship(
        "PhoneCall",
        back_populates="patient",
        foreign_keys="PhoneCall.patient_id",
    )

    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def age(self) -> int | None:
        """Calculate patient's age."""
        if not self.date_of_birth:
            return None
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age

    def __repr__(self) -> str:
        return f"<Patient {self.full_name} ({self.phone})>"
