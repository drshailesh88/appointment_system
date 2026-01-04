"""
Lab results models for test orders and results.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.patient import Patient


class LabOrderStatus(str, Enum):
    """Lab order status types."""

    ORDERED = "ordered"
    SAMPLE_COLLECTED = "sample_collected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class LabTestPriority(str, Enum):
    """Lab test priority."""

    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"  # Immediate


class LabResultStatus(str, Enum):
    """Lab result status."""

    PENDING = "pending"
    PRELIMINARY = "preliminary"
    FINAL = "final"
    CORRECTED = "corrected"
    AMENDED = "amended"


class LabOrder(BaseModel):
    """
    Lab order/requisition model.

    Attributes:
        patient_id: Patient for whom tests are ordered
        doctor_id: Doctor who ordered the tests
        appointment_id: Associated appointment (optional)
        order_date: When the order was placed
        tests_ordered: List of test names/codes requested
        priority: Order priority (routine, urgent, stat)
        status: Current order status
        clinical_notes: Clinical indication for tests
        diagnosis_codes: ICD-10 or similar codes
        sample_collected_at: When sample was collected
        expected_completion: Expected result date
        lab_provider: External lab name (if applicable)
        lab_order_id: External lab's order ID
    """

    __tablename__ = "lab_orders"

    # Relations
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=True,
        index=True,
    )

    # Order details
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    tests_ordered: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default=LabTestPriority.ROUTINE.value,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=LabOrderStatus.ORDERED.value,
        index=True,
    )

    # Clinical info
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis_codes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Sample & timing
    sample_collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expected_completion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # External lab integration
    lab_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lab_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Metadata
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="lab_orders")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="lab_orders")
    results: Mapped[list["LabResult"]] = relationship(
        "LabResult",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["LabReport"]] = relationship(
        "LabReport",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<LabOrder {self.id} ({self.status})>"


class LabResult(BaseModel):
    """
    Individual lab test result.

    Attributes:
        order_id: Associated lab order
        test_name: Name of the test (e.g., "Hemoglobin")
        test_code: Standard code (LOINC, local code)
        value: Test result value
        value_numeric: Numeric value for trending
        unit: Unit of measurement
        reference_range_min: Lower bound of normal range
        reference_range_max: Upper bound of normal range
        reference_range_text: Textual reference (e.g., "Negative", "< 200")
        is_abnormal: Flag for abnormal values
        abnormal_flag: Type of abnormality (H=high, L=low, etc.)
        status: Result status
        result_date: When result was finalized
        notes: Interpretation notes
        performed_by: Lab technician/analyzer
    """

    __tablename__ = "lab_results"

    # Relations
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lab_orders.id"),
        nullable=False,
        index=True,
    )

    # Test identification
    test_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    test_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    test_category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # CBC, LFT, etc.

    # Result value
    value: Mapped[str] = mapped_column(Text, nullable=False)  # Can be text or numeric
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)  # For trending
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Reference ranges
    reference_range_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_range_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_range_text: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Abnormality flags
    is_abnormal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    abnormal_flag: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # H, L, HH, LL, A

    # Status & timing
    status: Mapped[str] = mapped_column(
        String(20),
        default=LabResultStatus.FINAL.value,
    )
    result_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Additional info
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    methodology: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Metadata
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="results")

    @property
    def is_high(self) -> bool:
        """Check if value is above normal range."""
        if self.value_numeric is None or self.reference_range_max is None:
            return False
        return self.value_numeric > self.reference_range_max

    @property
    def is_low(self) -> bool:
        """Check if value is below normal range."""
        if self.value_numeric is None or self.reference_range_min is None:
            return False
        return self.value_numeric < self.reference_range_min

    def __repr__(self) -> str:
        return f"<LabResult {self.test_name}: {self.value} {self.unit or ''}>"


class LabReport(BaseModel):
    """
    Lab report document (PDF, HL7, etc.).

    Attributes:
        order_id: Associated lab order
        report_type: Type of report (pdf, hl7, text)
        file_path: Path to stored file
        file_url: External URL (if applicable)
        file_size: File size in bytes
        parsed_data: Extracted structured data
        raw_content: Raw text content
        received_at: When report was received
    """

    __tablename__ = "lab_reports"

    # Relations
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lab_orders.id"),
        nullable=False,
        index=True,
    )

    # Report details
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, hl7, text
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Parsed content
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="reports")

    def __repr__(self) -> str:
        return f"<LabReport {self.id} ({self.report_type})>"
