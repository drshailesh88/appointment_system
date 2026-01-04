"""
Health record schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HealthRecordBase(BaseModel):
    """Base health record schema."""

    patient_id: UUID
    metric_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of health metric (heart_rate, blood_pressure_systolic, etc.)",
    )
    value: float = Field(..., description="Numeric value of the metric")
    unit: str = Field(..., min_length=1, max_length=20, description="Unit of measurement")
    recorded_at: datetime = Field(..., description="When the measurement was taken")
    source: str = Field(
        default="manual",
        max_length=100,
        description="Source of the data (Apple Health, manual, etc.)",
    )
    device_id: Optional[str] = Field(
        None, max_length=100, description="Device identifier if available"
    )
    metadata: Optional[dict] = Field(None, description="Additional metadata")

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, v: str) -> str:
        """Validate metric type is one of the allowed types."""
        allowed_types = {
            "heart_rate",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "weight",
            "height",
            "body_temperature",
            "blood_glucose",
            "oxygen_saturation",
            "steps",
            "sleep_analysis",
            "active_energy_burned",
            "exercise_time",
            "respiratory_rate",
        }
        if v not in allowed_types:
            raise ValueError(f"Invalid metric type: {v}. Must be one of {allowed_types}")
        return v


class HealthRecordCreate(HealthRecordBase):
    """Schema for creating a health record."""

    pass


class HealthRecordBulkCreate(BaseModel):
    """Schema for bulk creating health records (sync from device)."""

    readings: list[HealthRecordCreate] = Field(
        ..., min_length=1, max_length=1000, description="List of health readings to create"
    )


class HealthRecordUpdate(BaseModel):
    """Schema for updating a health record."""

    value: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=20)
    recorded_at: Optional[datetime] = None
    source: Optional[str] = Field(None, max_length=100)
    device_id: Optional[str] = Field(None, max_length=100)
    metadata: Optional[dict] = None


class HealthRecordResponse(BaseModel):
    """Schema for health record response."""

    id: UUID
    patient_id: UUID
    metric_type: str
    value: float
    unit: str
    recorded_at: datetime
    source: str
    device_id: Optional[str]
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @property
    def is_abnormal(self) -> bool:
        """Check if the health reading is abnormal."""
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


class HealthSummaryResponse(BaseModel):
    """Schema for health summary response."""

    patient_id: UUID
    latest_heart_rate: Optional[HealthRecordResponse] = None
    latest_blood_pressure_systolic: Optional[HealthRecordResponse] = None
    latest_blood_pressure_diastolic: Optional[HealthRecordResponse] = None
    latest_weight: Optional[HealthRecordResponse] = None
    latest_oxygen_saturation: Optional[HealthRecordResponse] = None
    latest_blood_glucose: Optional[HealthRecordResponse] = None
    today_steps: Optional[int] = None
    today_sleep_hours: Optional[float] = None
    last_synced_at: Optional[datetime] = None
    total_readings: int = 0


class HealthRecordsFilter(BaseModel):
    """Schema for filtering health records."""

    metric_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class HealthSyncResponse(BaseModel):
    """Schema for health sync response."""

    success: bool
    synced_count: int
    failed_count: int = 0
    errors: list[str] = []
    last_synced_at: datetime
