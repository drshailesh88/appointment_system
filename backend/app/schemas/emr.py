"""
EMR Integration Schemas.

Pydantic schemas for EMR sync and timeline features.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TimelineEventType(str, Enum):
    """Type of timeline event."""

    APPOINTMENT = "appointment"
    VISIT = "visit"
    PROCEDURE = "procedure"
    PRESCRIPTION = "prescription"


class TimelineEventSource(str, Enum):
    """Source system for timeline event."""

    PRACTICE_MANAGER = "practice_manager"
    EMR = "emr"


class TimelineEvent(BaseModel):
    """
    Unified timeline event combining appointments, visits, and procedures.

    Provides a single view of patient's healthcare journey.
    """

    model_config = ConfigDict(from_attributes=True)

    event_type: TimelineEventType
    timestamp: datetime
    title: str
    description: Optional[str] = None
    doctor_name: str
    source: TimelineEventSource

    # Optional fields depending on event type
    status: Optional[str] = None
    outcome: Optional[str] = None
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    findings: Optional[str] = None
    notes: Optional[str] = None

    # IDs for linking back to source records
    appointment_id: Optional[str] = None
    visit_id: Optional[str] = None
    procedure_id: Optional[str] = None


class EMRPatientResponse(BaseModel):
    """Patient data from EMR."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    address: Optional[str] = None
    created_at: str
    updated_at: str


class EMRVisitResponse(BaseModel):
    """Visit/consultation record from EMR."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    doctor_name: str
    visit_date: str
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    vitals: Optional[dict[str, Any]] = None
    prescriptions: Optional[list[dict[str, Any]]] = None
    created_at: str


class EMRPrescriptionSummary(BaseModel):
    """Prescription summary from EMR visit."""

    visit_id: str
    visit_date: str
    doctor_name: str
    medications: list[dict[str, Any]] = Field(default_factory=list)
    instructions: Optional[str] = None


class EMRSyncStatusResponse(BaseModel):
    """EMR sync status response."""

    enabled: bool
    available: bool
    database_path: Optional[str] = None
    last_sync_time: Optional[datetime] = None
    sync_running: bool
    stats: dict[str, Any]
    sync_interval_seconds: int


class EMRSyncTriggerResponse(BaseModel):
    """Response for manual sync trigger."""

    message: str
    stats: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class PatientTimelineRequest(BaseModel):
    """Request parameters for patient timeline."""

    limit: int = Field(default=50, ge=1, le=500)
    include_appointments: bool = True
    include_visits: bool = True
    include_procedures: bool = True


class PatientTimelineResponse(BaseModel):
    """Patient timeline response."""

    patient_id: str
    patient_name: str
    total_events: int
    events: list[TimelineEvent]
    emr_available: bool
