"""
No-show prediction model for appointment management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.appointment import Appointment


class RiskLevel(str, Enum):
    """No-show risk level categories."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NoShowPrediction(BaseModel):
    """
    No-show prediction model for appointments.

    Stores ML predictions about likelihood of patient no-shows
    and recommended mitigation actions.

    Attributes:
        appointment_id: Associated appointment
        probability: Predicted no-show probability (0-1)
        risk_level: Categorized risk (low/medium/high)
        features_used: Feature values used for prediction
        model_version: Version of ML model used
        predicted_at: When prediction was made
        was_accurate: Whether prediction matched actual outcome (nullable)
        actual_outcome: Actual appointment status (filled post-appointment)
        mitigation_actions: Recommended actions to reduce no-show risk
    """

    __tablename__ = "noshow_predictions"

    # Appointment Reference
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Prediction Results
    probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    # Prediction Metadata
    features_used: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
    )
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    # Outcome Tracking (for model improvement)
    was_accurate: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    actual_outcome: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    feedback_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Mitigation Recommendations
    mitigation_actions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship(
        "Appointment",
        backref="noshow_prediction",
    )

    @property
    def risk_percentage(self) -> int:
        """Get risk as percentage."""
        return int(self.probability * 100)

    @property
    def is_high_risk(self) -> bool:
        """Check if appointment is high risk."""
        return self.risk_level == RiskLevel.HIGH.value

    @property
    def is_medium_risk(self) -> bool:
        """Check if appointment is medium risk."""
        return self.risk_level == RiskLevel.MEDIUM.value

    @property
    def is_low_risk(self) -> bool:
        """Check if appointment is low risk."""
        return self.risk_level == RiskLevel.LOW.value

    def __repr__(self) -> str:
        return f"<NoShowPrediction {self.id} ({self.risk_level} - {self.risk_percentage}%)>"
