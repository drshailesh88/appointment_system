"""
Procedure & Intervention Tracking Model.

Phase 9: Flexible procedure tracking for ANY medical specialty.

Use Cases:
- Cardiologist: Echos, Angioplasties, Stents, Pacemakers
- Orthopedist: Surgeries, Fracture fixations, Joint replacements
- Ophthalmologist: Cataract surgeries, LASIK, Injections
- Dermatologist: Biopsies, Procedures, Laser treatments
- Any specialty: Custom procedure types
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSONB, UUID


if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.clinic import Clinic
    from app.models.doctor import Doctor
    from app.models.patient import Patient


class ProcedureOutcome(str, Enum):
    """Procedure outcome status."""

    SUCCESSFUL = "successful"
    PARTIAL = "partial"
    UNSUCCESSFUL = "unsuccessful"
    COMPLICATED = "complicated"
    REFERRED = "referred"
    ABANDONED = "abandoned"
    PENDING_FOLLOWUP = "pending_followup"


class ProcedureSeverity(str, Enum):
    """Procedure severity/complexity level."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class Procedure(BaseModel):
    """
    Procedure/Intervention tracking model.

    Designed to be flexible for any medical specialty while providing
    structured fields for common use cases like cardiology procedures.

    Attributes:
        category: Broad category (e.g., "Cardiology", "Orthopedics")
        procedure_type: Specific type (e.g., "Echo", "Angioplasty", "Stent")
        sub_type: Further classification (e.g., "Stress Echo", "Drug-Eluting Stent")
        outcome: Result of the procedure
        severity: Complexity level
        consumables: JSON field for materials used (stent brand, implant details)
        findings: Clinical findings
        notes: Additional notes
        billing_code: ICD/CPT code for billing
        duration_minutes: How long the procedure took
        is_billable: Whether to include in billing
        billed_amount: Amount charged for procedure
    """

    __tablename__ = "procedures"

    # Core Relations
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(),
        ForeignKey("appointments.id"),
        nullable=True,
        index=True,
    )

    # Procedure Classification (Flexible for any specialty)
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    procedure_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    sub_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Procedure name (human readable)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timing
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Outcome & Severity
    outcome: Mapped[str] = mapped_column(
        String(30),
        default=ProcedureOutcome.SUCCESSFUL.value,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default=ProcedureSeverity.MINOR.value,
    )

    # Clinical Details
    findings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    complications: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Consumables & Materials (Flexible JSON for specialty-specific data)
    # Examples:
    # Cardiology: {"stent_brand": "Xience", "stent_size": "3.0x18mm", "quantity": 2}
    # Orthopedics: {"implant_type": "Hip Prosthesis", "manufacturer": "Zimmer", "lot_number": "XYZ123"}
    # Ophthalmology: {"lens_type": "Monofocal", "power": "+21.5D"}
    consumables: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Custom fields for specialty-specific data
    # Allows any specialty to store their specific measurements/values
    # Examples:
    # Cardiology: {"ef_before": 45, "ef_after": 55, "lesion_location": "LAD"}
    # Ophthalmology: {"preop_vision": "6/36", "postop_vision": "6/6"}
    custom_fields: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Billing
    billing_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    cpt_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    icd_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    is_billable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    billed_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Location (for hospitals with multiple procedure rooms)
    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Assistants/Team (for complex procedures)
    assistant_doctors: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Follow-up
    requires_followup: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    followup_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # EMR Integration
    emr_procedure_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    synced_to_emr: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Relationships
    clinic: Mapped["Clinic"] = relationship(
        "Clinic",
        back_populates="procedures",
    )
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="procedures",
    )
    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="procedures",
    )
    appointment: Mapped["Appointment | None"] = relationship(
        "Appointment",
        back_populates="procedure",
    )

    def __repr__(self) -> str:
        return f"<Procedure {self.procedure_type}: {self.name} ({self.outcome})>"


# Predefined procedure categories and types for common specialties
# These serve as templates but doctors can create custom ones

CARDIOLOGY_PROCEDURES = {
    "category": "Cardiology",
    "types": {
        "diagnostic": [
            "Echocardiogram",
            "Stress Echo",
            "TEE (Transesophageal Echo)",
            "Holter Monitoring",
            "ECG",
            "Treadmill Test",
            "Coronary Angiography",
        ],
        "interventional": [
            "Angioplasty (PTCA)",
            "Stent Placement",
            "Pacemaker Implantation",
            "ICD Implantation",
            "CRT Device",
            "Balloon Valvuloplasty",
            "TAVI/TAVR",
            "Catheter Ablation",
        ],
    },
}

ORTHOPEDICS_PROCEDURES = {
    "category": "Orthopedics",
    "types": {
        "diagnostic": [
            "Arthroscopy (Diagnostic)",
            "Joint Aspiration",
        ],
        "surgical": [
            "Total Knee Replacement",
            "Total Hip Replacement",
            "Fracture Fixation",
            "ACL Reconstruction",
            "Meniscus Repair",
            "Spine Surgery",
            "Shoulder Arthroscopy",
        ],
        "injection": [
            "Steroid Injection",
            "PRP Injection",
            "Hyaluronic Acid Injection",
        ],
    },
}

OPHTHALMOLOGY_PROCEDURES = {
    "category": "Ophthalmology",
    "types": {
        "surgical": [
            "Cataract Surgery",
            "LASIK",
            "PRK",
            "Glaucoma Surgery",
            "Vitrectomy",
            "Retinal Detachment Repair",
        ],
        "injection": [
            "Intravitreal Injection",
            "Anti-VEGF Injection",
        ],
        "laser": [
            "YAG Laser Capsulotomy",
            "Laser Photocoagulation",
            "SLT for Glaucoma",
        ],
    },
}

DERMATOLOGY_PROCEDURES = {
    "category": "Dermatology",
    "types": {
        "diagnostic": [
            "Skin Biopsy",
            "Dermoscopy",
        ],
        "surgical": [
            "Excision",
            "Mohs Surgery",
            "Cryotherapy",
        ],
        "cosmetic": [
            "Botox",
            "Filler Injection",
            "Chemical Peel",
            "Laser Treatment",
            "Microneedling",
        ],
    },
}

GASTROENTEROLOGY_PROCEDURES = {
    "category": "Gastroenterology",
    "types": {
        "endoscopy": [
            "Upper GI Endoscopy",
            "Colonoscopy",
            "ERCP",
            "EUS",
            "Capsule Endoscopy",
        ],
        "interventional": [
            "Polypectomy",
            "Variceal Banding",
            "PEG Tube Placement",
            "Stent Placement",
        ],
    },
}

# All predefined procedure templates
PROCEDURE_TEMPLATES = {
    "cardiology": CARDIOLOGY_PROCEDURES,
    "orthopedics": ORTHOPEDICS_PROCEDURES,
    "ophthalmology": OPHTHALMOLOGY_PROCEDURES,
    "dermatology": DERMATOLOGY_PROCEDURES,
    "gastroenterology": GASTROENTEROLOGY_PROCEDURES,
}
