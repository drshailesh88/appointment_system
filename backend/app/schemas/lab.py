"""
Lab results schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.lab_result import (
    LabOrderStatus,
    LabResultStatus,
    LabTestPriority,
)


# ============================================================
# Lab Order Schemas
# ============================================================


class LabOrderBase(BaseModel):
    """Base lab order schema."""

    patient_id: UUID
    doctor_id: UUID
    tests_ordered: list[str] = Field(..., min_length=1)
    priority: LabTestPriority = LabTestPriority.ROUTINE
    clinical_notes: str | None = None
    diagnosis_codes: list[str] | None = None


class LabOrderCreate(LabOrderBase):
    """Schema for creating a lab order."""

    appointment_id: UUID | None = None
    expected_completion: datetime | None = None
    lab_provider: str | None = None


class LabOrderUpdate(BaseModel):
    """Schema for updating a lab order."""

    status: LabOrderStatus | None = None
    sample_collected_at: datetime | None = None
    expected_completion: datetime | None = None
    lab_provider: str | None = None
    lab_order_id: str | None = None
    metadata: dict[str, Any] | None = None


class LabOrderResponse(BaseModel):
    """Schema for lab order response."""

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_id: UUID | None
    order_date: datetime
    tests_ordered: list[str]
    priority: str
    status: str
    clinical_notes: str | None
    diagnosis_codes: list[str] | None
    sample_collected_at: datetime | None
    expected_completion: datetime | None
    lab_provider: str | None
    lab_order_id: str | None
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    # Include related data
    patient_name: str | None = None
    doctor_name: str | None = None
    results_count: int = 0
    abnormal_count: int = 0

    model_config = {"from_attributes": True}


class LabOrderListResponse(BaseModel):
    """Schema for lab order list response."""

    orders: list[LabOrderResponse]
    total: int


# ============================================================
# Lab Result Schemas
# ============================================================


class LabResultBase(BaseModel):
    """Base lab result schema."""

    test_name: str
    test_code: str | None = None
    test_category: str | None = None
    value: str
    value_numeric: float | None = None
    unit: str | None = None
    reference_range_min: float | None = None
    reference_range_max: float | None = None
    reference_range_text: str | None = None
    is_abnormal: bool = False
    abnormal_flag: str | None = None
    notes: str | None = None


class LabResultCreate(LabResultBase):
    """Schema for creating a lab result."""

    order_id: UUID
    status: LabResultStatus = LabResultStatus.FINAL
    result_date: datetime | None = None
    performed_by: str | None = None
    methodology: str | None = None


class LabResultUpdate(BaseModel):
    """Schema for updating a lab result."""

    value: str | None = None
    value_numeric: float | None = None
    status: LabResultStatus | None = None
    is_abnormal: bool | None = None
    abnormal_flag: str | None = None
    notes: str | None = None


class LabResultResponse(BaseModel):
    """Schema for lab result response."""

    id: UUID
    order_id: UUID
    test_name: str
    test_code: str | None
    test_category: str | None
    value: str
    value_numeric: float | None
    unit: str | None
    reference_range_min: float | None
    reference_range_max: float | None
    reference_range_text: str | None
    is_abnormal: bool
    abnormal_flag: str | None
    status: str
    result_date: datetime | None
    notes: str | None
    performed_by: str | None
    methodology: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LabResultTrendPoint(BaseModel):
    """Single data point for trend chart."""

    date: datetime
    value: float
    is_abnormal: bool


class LabResultTrendResponse(BaseModel):
    """Trend data for a specific test."""

    test_name: str
    unit: str | None
    reference_range_min: float | None
    reference_range_max: float | None
    data_points: list[LabResultTrendPoint]


# ============================================================
# Lab Report Schemas
# ============================================================


class LabReportBase(BaseModel):
    """Base lab report schema."""

    report_type: str  # pdf, hl7, text
    file_path: str | None = None
    file_url: str | None = None


class LabReportCreate(LabReportBase):
    """Schema for creating a lab report."""

    order_id: UUID
    file_size: int | None = None
    mime_type: str | None = None
    parsed_data: dict[str, Any] | None = None
    raw_content: str | None = None
    received_at: datetime


class LabReportResponse(BaseModel):
    """Schema for lab report response."""

    id: UUID
    order_id: UUID
    report_type: str
    file_path: str | None
    file_url: str | None
    file_size: int | None
    mime_type: str | None
    parsed_data: dict[str, Any] | None
    received_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# Upload & Parsing Schemas
# ============================================================


class LabReportUploadResponse(BaseModel):
    """Response after uploading a lab report."""

    order_id: UUID
    report_id: UUID
    results_created: int
    parsing_errors: list[str] = []


class LabResultsBulkCreate(BaseModel):
    """Bulk create lab results."""

    order_id: UUID
    results: list[LabResultCreate]


# ============================================================
# Search & Filter Schemas
# ============================================================


class LabOrderFilter(BaseModel):
    """Filter criteria for lab orders."""

    patient_id: UUID | None = None
    doctor_id: UUID | None = None
    status: LabOrderStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    lab_provider: str | None = None


class LabResultFilter(BaseModel):
    """Filter criteria for lab results."""

    patient_id: UUID | None = None
    order_id: UUID | None = None
    test_name: str | None = None
    test_category: str | None = None
    is_abnormal: bool | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


# ============================================================
# Statistics Schemas
# ============================================================


class LabStatistics(BaseModel):
    """Lab statistics."""

    total_orders: int
    pending_orders: int
    completed_orders: int
    total_results: int
    abnormal_results: int
    most_ordered_tests: list[dict[str, Any]]
    average_turnaround_hours: float | None
