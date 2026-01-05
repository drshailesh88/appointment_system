"""
Slot optimizer schemas for AI-powered scheduling recommendations.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OptimalSlot(BaseModel):
    """
    Optimal slot recommendation with scoring.

    Attributes:
        slot_time: Recommended appointment time
        score: Optimization score (0-100, higher is better)
        reasons: Explanation for recommendation
        efficiency_impact: Impact on daily schedule efficiency
        utilization_improvement: Expected utilization improvement percentage
        gap_reduction: Reduction in schedule gaps (minutes)
    """

    slot_time: datetime
    score: float = Field(ge=0, le=100)
    reasons: list[str]
    efficiency_impact: str
    utilization_improvement: float = Field(default=0.0, ge=0, le=100)
    gap_reduction: int = Field(default=0, ge=0)
    nearby_appointment_types: list[str] = Field(default_factory=list)


class SlotRecommendationRequest(BaseModel):
    """Request for slot recommendations."""

    doctor_id: UUID
    date_range_start: date
    date_range_end: date
    duration_minutes: int = Field(default=15, ge=5, le=120)
    appointment_type: str | None = None
    patient_id: UUID | None = None
    max_recommendations: int = Field(default=5, ge=1, le=20)
    constraints: dict[str, Any] | None = None


class SlotRecommendationResponse(BaseModel):
    """Response with recommended slots."""

    doctor_id: UUID
    doctor_name: str
    date_range_start: date
    date_range_end: date
    recommended_slots: list[OptimalSlot]
    current_utilization: float
    potential_utilization: float


class ScheduleGap(BaseModel):
    """Represents a gap in the schedule."""

    gap_start: datetime
    gap_end: datetime
    duration_minutes: int
    is_fillable: bool
    reason: str
    recommended_action: str


class ScheduleAnalysis(BaseModel):
    """
    Analysis of current schedule efficiency.

    Attributes:
        doctor_id: Doctor being analyzed
        date: Date being analyzed
        utilization_rate: Percentage of time utilized (0-100)
        gap_count: Number of gaps in schedule
        total_gap_minutes: Total minutes of gaps
        longest_gap_minutes: Duration of longest gap
        appointment_count: Number of appointments
        working_hours: Total working hours
        suggestions: List of improvement suggestions
        efficiency_score: Overall efficiency score (0-100)
    """

    doctor_id: UUID
    doctor_name: str
    date: date
    utilization_rate: float = Field(ge=0, le=100)
    gap_count: int = Field(ge=0)
    total_gap_minutes: int = Field(ge=0)
    longest_gap_minutes: int = Field(ge=0)
    appointment_count: int = Field(ge=0)
    working_hours: int = Field(ge=0)
    suggestions: list[str]
    efficiency_score: float = Field(ge=0, le=100)
    gaps: list[ScheduleGap] = Field(default_factory=list)


class UtilizationMetric(BaseModel):
    """Utilization metric for a time period."""

    label: str  # Hour/Day label
    utilization_rate: float = Field(ge=0, le=100)
    booked_slots: int
    available_slots: int
    gap_minutes: int


class UtilizationMetrics(BaseModel):
    """
    Utilization metrics breakdown.

    Provides granular utilization data by hour and day of week.
    """

    doctor_id: UUID
    doctor_name: str
    date_range_start: date
    date_range_end: date
    by_hour: list[UtilizationMetric]
    by_day: list[UtilizationMetric]
    overall_utilization: float = Field(ge=0, le=100)
    peak_hours: list[int] = Field(default_factory=list)
    low_hours: list[int] = Field(default_factory=list)
    trends: dict[str, Any] = Field(default_factory=dict)


class ScheduleAdjustment(BaseModel):
    """Suggested schedule adjustment."""

    adjustment_type: str  # "slot_duration", "working_hours", "break_time", etc.
    current_value: Any
    suggested_value: Any
    reason: str
    expected_improvement: float = Field(ge=0, le=100)
    priority: str  # "high", "medium", "low"


class ScheduleOptimizationSuggestions(BaseModel):
    """
    Comprehensive schedule optimization suggestions.

    Provides actionable recommendations to improve schedule efficiency.
    """

    doctor_id: UUID
    doctor_name: str
    current_efficiency_score: float = Field(ge=0, le=100)
    potential_efficiency_score: float = Field(ge=0, le=100)
    adjustments: list[ScheduleAdjustment]
    summary: str
    estimated_impact: dict[str, Any] = Field(default_factory=dict)


class GapIdentificationResponse(BaseModel):
    """Response for gap identification."""

    doctor_id: UUID
    doctor_name: str
    date: date
    gaps: list[ScheduleGap]
    total_gap_minutes: int
    fillable_gap_count: int
    recommendations: list[str]
