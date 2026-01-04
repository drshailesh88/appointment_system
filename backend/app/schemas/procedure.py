"""
Procedure & Intervention schemas.

Phase 9: Schemas for flexible procedure tracking across all specialties.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.procedure import ProcedureOutcome, ProcedureSeverity


class ProcedureBase(BaseModel):
    """Base procedure schema."""

    category: str = Field(..., min_length=1, max_length=100)
    procedure_type: str = Field(..., min_length=1, max_length=100)
    sub_type: str | None = Field(None, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ProcedureCreate(ProcedureBase):
    """Schema for creating a procedure."""

    patient_id: UUID
    doctor_id: UUID
    appointment_id: UUID | None = None

    # Timing
    performed_at: datetime | None = None  # Defaults to now
    duration_minutes: int | None = Field(None, ge=1, le=1440)

    # Outcome
    outcome: ProcedureOutcome = ProcedureOutcome.SUCCESSFUL
    severity: ProcedureSeverity = ProcedureSeverity.MINOR

    # Clinical Details
    findings: str | None = None
    notes: str | None = None
    complications: str | None = None

    # Consumables (flexible JSON for specialty-specific data)
    # Examples:
    # Cardiology: {"stent_brand": "Xience", "stent_size": "3.0x18mm", "quantity": 2}
    # Orthopedics: {"implant_type": "Hip", "manufacturer": "Zimmer"}
    consumables: dict[str, Any] | None = None

    # Custom fields for specialty-specific measurements
    # Examples:
    # Cardiology: {"ef_before": 45, "ef_after": 55}
    # Ophthalmology: {"preop_vision": "6/36", "postop_vision": "6/6"}
    custom_fields: dict[str, Any] | None = None

    # Billing
    billing_code: str | None = Field(None, max_length=20)
    cpt_code: str | None = Field(None, max_length=20)
    icd_code: str | None = Field(None, max_length=20)
    is_billable: bool = True
    billed_amount: Decimal | None = Field(None, ge=0)

    # Location & Team
    location: str | None = Field(None, max_length=100)
    assistant_doctors: list[str] | None = None

    # Follow-up
    requires_followup: bool = False
    followup_notes: str | None = None


class ProcedureUpdate(BaseModel):
    """Schema for updating a procedure."""

    category: str | None = Field(None, max_length=100)
    procedure_type: str | None = Field(None, max_length=100)
    sub_type: str | None = Field(None, max_length=100)
    name: str | None = Field(None, max_length=255)
    description: str | None = None

    performed_at: datetime | None = None
    duration_minutes: int | None = Field(None, ge=1, le=1440)

    outcome: ProcedureOutcome | None = None
    severity: ProcedureSeverity | None = None

    findings: str | None = None
    notes: str | None = None
    complications: str | None = None

    consumables: dict[str, Any] | None = None
    custom_fields: dict[str, Any] | None = None

    billing_code: str | None = None
    cpt_code: str | None = None
    icd_code: str | None = None
    is_billable: bool | None = None
    billed_amount: Decimal | None = None

    location: str | None = None
    assistant_doctors: list[str] | None = None

    requires_followup: bool | None = None
    followup_notes: str | None = None


class ProcedureResponse(BaseModel):
    """Schema for procedure response."""

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_id: UUID | None
    clinic_id: UUID

    category: str
    procedure_type: str
    sub_type: str | None
    name: str
    description: str | None

    performed_at: datetime
    duration_minutes: int | None

    outcome: str
    severity: str

    findings: str | None
    notes: str | None
    complications: str | None

    consumables: dict[str, Any] | None
    custom_fields: dict[str, Any] | None

    billing_code: str | None
    cpt_code: str | None
    icd_code: str | None
    is_billable: bool
    billed_amount: float | None

    location: str | None
    assistant_doctors: list[str] | None

    requires_followup: bool
    followup_notes: str | None

    emr_procedure_id: str | None
    synced_to_emr: bool

    created_at: datetime
    updated_at: datetime

    # Nested details (populated when needed)
    patient_name: str | None = None
    doctor_name: str | None = None

    model_config = {"from_attributes": True}


class ProcedureListResponse(BaseModel):
    """Schema for listing procedures."""

    id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    category: str
    procedure_type: str
    name: str
    performed_at: datetime
    outcome: str
    severity: str
    is_billable: bool
    billed_amount: float | None

    model_config = {"from_attributes": True}


# ========== Analytics Schemas ==========

class ProcedureStats(BaseModel):
    """Procedure statistics for a time period."""

    total: int
    by_category: dict[str, int]
    by_type: dict[str, int]
    by_outcome: dict[str, int]
    by_severity: dict[str, int]
    total_billed: float
    average_duration_minutes: float | None


class ProcedureTypeCount(BaseModel):
    """Count of procedures by type."""

    category: str
    procedure_type: str
    count: int
    total_billed: float


class DoctorProcedureStats(BaseModel):
    """Procedure statistics per doctor."""

    doctor_id: UUID
    doctor_name: str
    total_procedures: int
    by_category: dict[str, int]
    total_billed: float
    success_rate: float


class ProcedureTrend(BaseModel):
    """Daily procedure trend."""

    date: datetime
    count: int
    categories: dict[str, int]
    total_billed: float


# ========== Template Schemas ==========

class ProcedureTypeTemplate(BaseModel):
    """Template for a procedure type."""

    procedure_type: str
    sub_types: list[str] | None = None
    default_duration: int | None = None
    default_billing_code: str | None = None
    required_fields: list[str] | None = None


class ProcedureCategoryTemplate(BaseModel):
    """Template for a procedure category."""

    category: str
    types: dict[str, list[str]]


class ProcedureTemplatesResponse(BaseModel):
    """Response with all procedure templates."""

    templates: dict[str, ProcedureCategoryTemplate]


# ========== Quick Log Schemas ==========

class ProcedureQuickLog(BaseModel):
    """Schema for quick procedure logging (minimal fields)."""

    patient_id: UUID
    category: str
    procedure_type: str
    name: str
    outcome: ProcedureOutcome = ProcedureOutcome.SUCCESSFUL
    notes: str | None = None
    consumables: dict[str, Any] | None = None
    billed_amount: Decimal | None = None


class CardiacProcedureLog(BaseModel):
    """Specialized schema for cardiac procedures."""

    patient_id: UUID
    procedure_type: str  # Echo, Angioplasty, Stent, etc.
    name: str

    # Cardiac-specific fields
    ef_before: float | None = Field(None, ge=0, le=100)
    ef_after: float | None = Field(None, ge=0, le=100)
    lesion_location: str | None = None  # LAD, LCX, RCA, etc.

    # Stent-specific
    stent_brand: str | None = None
    stent_size: str | None = None
    stent_quantity: int | None = Field(None, ge=1)

    outcome: ProcedureOutcome = ProcedureOutcome.SUCCESSFUL
    complications: str | None = None
    notes: str | None = None
    billed_amount: Decimal | None = None


class OphthalmologyProcedureLog(BaseModel):
    """Specialized schema for ophthalmology procedures."""

    patient_id: UUID
    procedure_type: str  # Cataract, LASIK, Injection, etc.
    name: str
    eye: str = Field(..., pattern="^(left|right|both)$")

    # Vision-specific
    preop_vision: str | None = None  # e.g., "6/36"
    postop_vision: str | None = None  # e.g., "6/6"

    # Lens-specific
    lens_type: str | None = None
    lens_power: str | None = None

    outcome: ProcedureOutcome = ProcedureOutcome.SUCCESSFUL
    complications: str | None = None
    notes: str | None = None
    billed_amount: Decimal | None = None
