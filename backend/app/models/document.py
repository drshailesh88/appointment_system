"""
Document model for scanned document management.

Phase 10: Document Scanner & OCR
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.patient import Patient


class Document(BaseModel):
    """
    Document model for scanned patient records.

    Attributes:
        patient_id: Associated patient
        clinic_id: Associated clinic
        file_path: Relative path to stored document file
        file_type: MIME type (image/jpeg, image/png, application/pdf)
        original_filename: Original filename from upload
        file_size: File size in bytes
        page_count: Number of pages (for multi-page docs)
        ocr_text: Extracted text from OCR
        ocr_language: Detected language(s) of the text
        ocr_confidence: OCR confidence score (0-100)
        extracted_data: Structured data extracted from OCR (JSON)
        document_type: Type of document (lab_report, prescription, etc.)
        scan_date: When the document was scanned
        emr_document_id: Link to EMR system for sync
        synced_to_emr: Whether pushed to EMR
        is_processed: Whether OCR has been run
    """

    __tablename__ = "documents"

    # Core Relations
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )

    # File Information
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    page_count: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )

    # Document Classification
    document_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    scan_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # OCR Data
    is_processed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    ocr_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    ocr_language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    ocr_confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    # Extracted Structured Data (JSON)
    # Examples:
    # Lab Report: {"patient_name": "...", "test_date": "...", "tests": [...]}
    # Prescription: {"medicines": [...], "doctor_name": "...", "date": "..."}
    # Medical History: {"diagnoses": [...], "surgeries": [...]}
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Tags for search and organization
    tags: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Notes/Annotations
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # EMR Integration
    emr_document_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    synced_to_emr: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    # Relationships
    clinic: Mapped["Clinic"] = relationship(
        "Clinic",
        back_populates="documents",
    )
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return f"<Document {self.original_filename} for Patient {self.patient_id}>"


# Document type constants
DOCUMENT_TYPES = [
    "lab_report",
    "prescription",
    "radiology",
    "medical_history",
    "insurance",
    "consent_form",
    "discharge_summary",
    "referral_letter",
    "test_result",
    "imaging",
    "pathology",
    "ecg_report",
    "echo_report",
    "other",
]
