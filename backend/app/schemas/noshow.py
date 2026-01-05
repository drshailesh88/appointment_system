"""
No-show prediction schemas for API requests and responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.noshow_prediction import RiskLevel


class NoShowPredictionCreate(BaseModel):
    """Schema for creating a no-show prediction."""

    appointment_id: UUID


class NoShowPredictionResponse(BaseModel):
    """Schema for no-show prediction response."""

    id: UUID
    appointment_id: UUID
    probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    risk_percentage: int
    is_high_risk: bool
    is_medium_risk: bool
    is_low_risk: bool
    features_used: dict[str, Any]
    model_version: str
    predicted_at: datetime
    mitigation_actions: dict[str, Any] | None
    was_accurate: bool | None = None
    actual_outcome: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoShowBatchRequest(BaseModel):
    """Schema for batch prediction request."""

    appointment_ids: list[UUID] = Field(..., min_length=1, max_length=100)


class NoShowBatchResponse(BaseModel):
    """Schema for batch prediction response."""

    predictions: list[NoShowPredictionResponse]
    total_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class NoShowFeedbackRequest(BaseModel):
    """Schema for submitting prediction feedback."""

    appointment_id: UUID
    actual_status: str = Field(..., regex="^(completed|no_show|cancelled)$")


class NoShowFeedbackResponse(BaseModel):
    """Schema for feedback response."""

    success: bool
    message: str
    was_accurate: bool | None = None


class ModelStats(BaseModel):
    """Schema for model performance statistics."""

    model_version: str
    total_predictions: int
    accurate_predictions: int
    accuracy: float
    has_trained_model: bool
    risk_distribution: dict[str, int]


class ModelRetrainRequest(BaseModel):
    """Schema for model retraining request."""

    min_samples: int = Field(default=100, ge=50, le=10000)


class ModelRetrainResponse(BaseModel):
    """Schema for model retraining response."""

    success: bool
    message: str | None = None
    model_version: str | None = None
    total_samples: int | None = None
    training_samples: int | None = None
    test_samples: int | None = None
    train_accuracy: float | None = None
    test_accuracy: float | None = None
    no_show_rate: float | None = None


class HighRiskAppointment(BaseModel):
    """Schema for high-risk appointment list item."""

    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    scheduled_start: datetime
    probability: float
    risk_percentage: int
    mitigation_actions: dict[str, Any] | None

    model_config = {"from_attributes": True}


class HighRiskAppointmentListResponse(BaseModel):
    """Schema for high-risk appointments list."""

    appointments: list[HighRiskAppointment]
    total_count: int
    date_range_start: datetime
    date_range_end: datetime
