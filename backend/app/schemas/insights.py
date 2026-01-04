"""
Pydantic schemas for Proactive Insights.

Phase 16c: Practice AI - Proactive Intelligence
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProactiveInsightBase(BaseModel):
    """Base schema for proactive insights."""

    insight_type: str = Field(..., description="Type of insight")
    priority: int = Field(..., ge=1, le=5, description="Priority (1-5)")
    title: str = Field(..., max_length=255, description="Insight title")
    message: str = Field(..., description="Insight message")
    suggested_action: Optional[dict[str, Any]] = Field(
        None,
        description="Suggested action (one-click)",
    )
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")
    expires_at: Optional[datetime] = Field(None, description="When insight expires")


class ProactiveInsightCreate(ProactiveInsightBase):
    """Schema for creating a proactive insight."""

    clinic_id: UUID
    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None


class ProactiveInsightResponse(ProactiveInsightBase):
    """Schema for proactive insight response."""

    id: UUID
    clinic_id: UUID
    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    dismissed_at: Optional[datetime] = None
    dismissed_by_id: Optional[UUID] = None
    acted_at: Optional[datetime] = None
    acted_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FollowupScheduleBase(BaseModel):
    """Base schema for follow-up schedules."""

    due_date: datetime
    reason: str = Field(..., max_length=255)
    priority: int = Field(..., ge=1, le=5)


class FollowupScheduleCreate(FollowupScheduleBase):
    """Schema for creating a follow-up schedule."""

    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    procedure_id: UUID


class FollowupScheduleResponse(FollowupScheduleBase):
    """Schema for follow-up schedule response."""

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    procedure_id: UUID
    notified_at: Optional[datetime] = None
    completed: bool
    scheduled_appointment_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SuggestedFollowup(BaseModel):
    """Schema for suggested follow-up."""

    days_from_procedure: int
    reason: str
    priority: int
    condition: Optional[str] = None  # e.g., "ef_below_40"


class UserDigestPreferencesBase(BaseModel):
    """Base schema for user digest preferences."""

    enabled: bool = True
    delivery_hour: int = Field(8, ge=0, le=23)
    delivery_minute: int = Field(0, ge=0, le=59)
    channels: list[str] = Field(default_factory=lambda: ["push"])
    include_revenue: bool = True
    include_appointments: bool = True
    include_followups: bool = True
    include_schedule_gaps: bool = True
    include_waitlist: bool = True


class UserDigestPreferencesCreate(UserDigestPreferencesBase):
    """Schema for creating digest preferences."""

    user_id: UUID
    clinic_id: UUID


class UserDigestPreferencesUpdate(BaseModel):
    """Schema for updating digest preferences."""

    enabled: Optional[bool] = None
    delivery_hour: Optional[int] = Field(None, ge=0, le=23)
    delivery_minute: Optional[int] = Field(None, ge=0, le=59)
    channels: Optional[list[str]] = None
    include_revenue: Optional[bool] = None
    include_appointments: Optional[bool] = None
    include_followups: Optional[bool] = None
    include_schedule_gaps: Optional[bool] = None
    include_waitlist: Optional[bool] = None


class UserDigestPreferencesResponse(UserDigestPreferencesBase):
    """Schema for digest preferences response."""

    id: UUID
    user_id: UUID
    clinic_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyDigest(BaseModel):
    """Schema for daily digest."""

    date: datetime
    appointments_today: int
    revenue_yesterday: float
    pending_followups: list[ProactiveInsightResponse]
    schedule_alerts: list[ProactiveInsightResponse]
    waitlist_opportunities: list[ProactiveInsightResponse]
    key_insights: list[ProactiveInsightResponse]


class TimeGap(BaseModel):
    """Schema for schedule gap."""

    start_time: datetime
    end_time: datetime
    duration_minutes: int
    doctor_id: UUID
    doctor_name: str


class BufferSuggestion(BaseModel):
    """Schema for buffer time suggestion."""

    suggested_duration_minutes: int
    reason: str
    confidence: float  # 0.0 - 1.0


class OverbookingRisk(BaseModel):
    """Schema for overbooking risk assessment."""

    risk_level: str  # "low", "medium", "high"
    total_procedures: int
    estimated_duration_minutes: int
    available_minutes: int
    recommendations: list[str]


class FollowupReminder(BaseModel):
    """Schema for follow-up reminder."""

    patient_id: UUID
    patient_name: str
    procedure_type: str
    procedure_date: datetime
    due_date: datetime
    reason: str
    priority: int
    days_overdue: int


class InsightListResponse(BaseModel):
    """Schema for list of insights."""

    insights: list[ProactiveInsightResponse]
    total: int
    page: int
    page_size: int
