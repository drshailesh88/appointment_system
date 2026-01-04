"""
Health record model for storing health data from Apple Health and other sources.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.patient import Patient


class HealthRecord(BaseModel):
    """
    Health record model for storing health metrics.

    Stores health data synced from Apple Health or manually entered.
    Supports various health metrics like heart rate, blood pressure, weight, etc.

    Attributes:
        patient_id: Associated patient
        metric_type: Type of health metric (heart_rate, blood_pressure_systolic, etc.)
        value: Numeric value of the metric
        unit: Unit of measurement (bpm, mmHg, kg, etc.)
        recorded_at: When the measurement was taken (not when synced)
        source: Where the data came from (Apple Health, manual entry, etc.)
        device_id: Device identifier if available
        metadata: Additional metadata in JSON format
    """

    __tablename__ = "health_records"

    # Patient relationship
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Metric information
    metric_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # heart_rate, blood_pressure_systolic, etc.
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # bpm, mmHg, kg, etc.

    # Timing
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Source information
    source: Mapped[str] = mapped_column(
        String(100), nullable=False, default="manual"
    )  # Apple Health, manual, device name
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Additional data
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="health_records",
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index(
            "ix_health_records_patient_metric_time",
            "patient_id",
            "metric_type",
            "recorded_at",
        ),
        Index(
            "ix_health_records_patient_time",
            "patient_id",
            "recorded_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<HealthRecord {self.metric_type}={self.value}{self.unit} for patient {self.patient_id}>"

    @property
    def is_abnormal(self) -> bool:
        """
        Check if the health reading is abnormal based on basic thresholds.

        Note: These are general guidelines. Always consult with healthcare professionals
        for proper interpretation.
        """
        if self.metric_type == "heart_rate":
            return self.value < 60 or self.value > 100
        elif self.metric_type == "blood_pressure_systolic":
            return self.value < 90 or self.value > 140
        elif self.metric_type == "blood_pressure_diastolic":
            return self.value < 60 or self.value > 90
        elif self.metric_type == "oxygen_saturation":
            return self.value < 95
        elif self.metric_type == "blood_glucose":
            return self.value < 70 or self.value > 140
        elif self.metric_type == "body_temperature":
            return self.value < 36.1 or self.value > 37.2
        else:
            return False


# Add health_records relationship to Patient model
# This needs to be added to the Patient model in patient.py
# health_records: Mapped[list["HealthRecord"]] = relationship(
#     "HealthRecord",
#     back_populates="patient",
#     cascade="all, delete-orphan",
# )
