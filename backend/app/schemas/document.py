"""
Document schemas for scanned document management.

Phase 10: Document Scanner & OCR
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema."""

    patient_id: UUID
    document_type: str | None = Field(None, max_length=50)
    notes: str | None = None
    tags: list[str] | None = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document (during upload)."""

    original_filename: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., max_length=100)
    file_size: int | None = Field(None, ge=0)
    page_count: int = Field(default=1, ge=1)


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    document_type: str | None = Field(None, max_length=50)
    notes: str | None = None
    tags: list[str] | None = None
    extracted_data: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: UUID
    patient_id: UUID
    clinic_id: UUID

    file_path: str
    file_type: str
    original_filename: str
    file_size: int | None
    page_count: int

    document_type: str | None
    scan_date: datetime

    is_processed: bool
    ocr_text: str | None
    ocr_language: str | None
    ocr_confidence: float | None
    extracted_data: dict[str, Any] | None

    tags: list[str] | None
    notes: str | None

    emr_document_id: str | None
    synced_to_emr: bool

    created_at: datetime
    updated_at: datetime

    # Nested details (populated when needed)
    patient_name: str | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Schema for listing documents."""

    id: UUID
    patient_id: UUID
    patient_name: str
    original_filename: str
    file_type: str
    document_type: str | None
    scan_date: datetime
    is_processed: bool
    file_size: int | None
    page_count: int

    model_config = {"from_attributes": True}


class DocumentOCRRequest(BaseModel):
    """Schema for OCR processing request."""

    languages: list[str] = Field(
        default=["en", "hi"],
        description="Languages for OCR detection (e.g., 'en', 'hi')",
    )
    extract_structured_data: bool = Field(
        default=True,
        description="Attempt to extract structured data from the text",
    )


class DocumentOCRResponse(BaseModel):
    """Schema for OCR processing response."""

    id: UUID
    is_processed: bool
    ocr_text: str | None
    ocr_language: str | None
    ocr_confidence: float | None
    extracted_data: dict[str, Any] | None
    processing_time_seconds: float


class DocumentTextResponse(BaseModel):
    """Schema for document text extraction."""

    id: UUID
    original_filename: str
    ocr_text: str | None
    is_processed: bool
    extracted_data: dict[str, Any] | None


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""

    id: UUID
    file_path: str
    original_filename: str
    file_type: str
    file_size: int | None
    message: str


class DocumentStats(BaseModel):
    """Document statistics."""

    total: int
    by_type: dict[str, int]
    processed: int
    unprocessed: int
    total_size_mb: float


class PatientDocumentSummary(BaseModel):
    """Patient document summary."""

    patient_id: UUID
    patient_name: str
    total_documents: int
    by_type: dict[str, int]
    latest_document_date: datetime | None
