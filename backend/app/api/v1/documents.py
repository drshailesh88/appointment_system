"""
Document Scanner & OCR API endpoints.

Phase 10: Document Scanner & OCR
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession
from app.models.document import DOCUMENT_TYPES, Document
from app.models.patient import Patient
from app.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentOCRRequest,
    DocumentOCRResponse,
    DocumentResponse,
    DocumentStats,
    DocumentTextResponse,
    DocumentUpdate,
    DocumentUploadResponse,
    PatientDocumentSummary,
)
from app.services.ocr import get_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter()

# File upload settings
UPLOAD_DIR = Path("uploads/documents")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_upload_directory() -> Path:
    """Get or create upload directory."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ========== Response Models ==========


class DocumentListWithCount(BaseModel):
    """Paginated document list response."""

    items: list[DocumentListResponse]
    total: int
    limit: int
    offset: int


class DocumentTypeList(BaseModel):
    """List of available document types."""

    types: list[str]


# ========== Upload Endpoint ==========


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    document_type: str | None = Form(None),
    notes: str | None = Form(None),
    tags: str | None = Form(None),  # JSON string or comma-separated
):
    """
    Upload a scanned document.

    Args:
        file: Image file (JPEG, PNG, PDF, TIFF)
        patient_id: Patient UUID
        document_type: Type of document (optional)
        notes: Additional notes (optional)
        tags: Tags as JSON array or comma-separated string (optional)

    Returns:
        Document upload response with file details
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate patient
    try:
        patient_uuid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid patient ID",
        )

    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_uuid,
            Patient.clinic_id == current_user.clinic_id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Read file
    try:
        contents = await file.read()
        file_size = len(contents)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB",
            )
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read file",
        )

    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"

    # Create clinic-specific subdirectory
    clinic_dir = get_upload_directory() / str(current_user.clinic_id)
    clinic_dir.mkdir(parents=True, exist_ok=True)

    file_path = clinic_dir / unique_filename
    relative_path = f"uploads/documents/{current_user.clinic_id}/{unique_filename}"

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
        logger.info(f"Saved document: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file",
        )

    # Parse tags if provided
    parsed_tags = None
    if tags:
        try:
            # Try JSON first
            import json

            parsed_tags = json.loads(tags)
        except json.JSONDecodeError:
            # Fall back to comma-separated
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    # Create document record
    document = Document(
        clinic_id=current_user.clinic_id,
        patient_id=patient_uuid,
        file_path=relative_path,
        file_type=file.content_type or f"image/{file_ext[1:]}",
        original_filename=file.filename,
        file_size=file_size,
        document_type=document_type,
        notes=notes,
        tags=parsed_tags,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return DocumentUploadResponse(
        id=document.id,
        file_path=document.file_path,
        original_filename=document.original_filename,
        file_type=document.file_type,
        file_size=document.file_size,
        message="Document uploaded successfully",
    )


# ========== OCR Endpoint ==========


@router.post("/{document_id}/ocr", response_model=DocumentOCRResponse)
async def process_ocr(
    document_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    ocr_request: DocumentOCRRequest = DocumentOCRRequest(),
):
    """
    Process OCR on a document.

    Extracts text from the scanned document using EasyOCR.

    Args:
        document_id: Document UUID
        ocr_request: OCR processing options

    Returns:
        OCR results with extracted text and structured data
    """
    import time

    start_time = time.time()

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.clinic_id == current_user.clinic_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if file exists
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on disk",
        )

    # Run OCR
    try:
        ocr_service = get_ocr_service()
        ocr_result = ocr_service.process_document(
            file_path,
            languages=ocr_request.languages,
            extract_structured=ocr_request.extract_structured_data,
        )

        # Update document with OCR results
        document.is_processed = True
        document.ocr_text = ocr_result.get("ocr_text")
        document.ocr_language = ocr_result.get("ocr_language")
        document.ocr_confidence = ocr_result.get("ocr_confidence")
        document.extracted_data = ocr_result.get("extracted_data", {})

        await db.commit()
        await db.refresh(document)

        processing_time = time.time() - start_time

        return DocumentOCRResponse(
            id=document.id,
            is_processed=document.is_processed,
            ocr_text=document.ocr_text,
            ocr_language=document.ocr_language,
            ocr_confidence=document.ocr_confidence,
            extracted_data=document.extracted_data,
            processing_time_seconds=round(processing_time, 2),
        )

    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )


# ========== CRUD Endpoints ==========


@router.get("", response_model=DocumentListWithCount)
async def list_documents(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: uuid.UUID | None = Query(None),
    document_type: str | None = Query(None),
    is_processed: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List documents with optional filters.

    Args:
        patient_id: Filter by patient (optional)
        document_type: Filter by document type (optional)
        is_processed: Filter by OCR processing status (optional)
        limit: Number of results (default: 50)
        offset: Pagination offset (default: 0)

    Returns:
        Paginated list of documents
    """
    # Build query
    query = (
        select(Document)
        .where(Document.clinic_id == current_user.clinic_id)
        .options(joinedload(Document.patient))
    )

    if patient_id:
        query = query.where(Document.patient_id == patient_id)

    if document_type:
        query = query.where(Document.document_type == document_type)

    if is_processed is not None:
        query = query.where(Document.is_processed == is_processed)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    documents = result.scalars().all()

    # Format response
    items = [
        DocumentListResponse(
            id=doc.id,
            patient_id=doc.patient_id,
            patient_name=doc.patient.full_name,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            document_type=doc.document_type,
            scan_date=doc.scan_date,
            is_processed=doc.is_processed,
            file_size=doc.file_size,
            page_count=doc.page_count,
        )
        for doc in documents
    ]

    return DocumentListWithCount(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/patient/{patient_id}", response_model=list[DocumentResponse])
async def get_patient_documents(
    patient_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get all documents for a patient.

    Args:
        patient_id: Patient UUID

    Returns:
        List of documents for the patient
    """
    # Verify patient belongs to clinic
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == current_user.clinic_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Get documents
    result = await db.execute(
        select(Document)
        .where(
            Document.patient_id == patient_id,
            Document.clinic_id == current_user.clinic_id,
        )
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    # Add patient name to each document
    response_docs = []
    for doc in documents:
        doc_dict = DocumentResponse.model_validate(doc).model_dump()
        doc_dict["patient_name"] = patient.full_name
        response_docs.append(DocumentResponse(**doc_dict))

    return response_docs


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get a specific document by ID.

    Args:
        document_id: Document UUID

    Returns:
        Document details
    """
    result = await db.execute(
        select(Document)
        .where(
            Document.id == document_id,
            Document.clinic_id == current_user.clinic_id,
        )
        .options(joinedload(Document.patient))
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Add patient name
    doc_dict = DocumentResponse.model_validate(document).model_dump()
    doc_dict["patient_name"] = document.patient.full_name

    return DocumentResponse(**doc_dict)


@router.get("/{document_id}/text", response_model=DocumentTextResponse)
async def get_document_text(
    document_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get extracted text from a document.

    Args:
        document_id: Document UUID

    Returns:
        Extracted OCR text and structured data
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.clinic_id == current_user.clinic_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentTextResponse(
        id=document.id,
        original_filename=document.original_filename,
        ocr_text=document.ocr_text,
        is_processed=document.is_processed,
        extracted_data=document.extracted_data,
    )


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    data: DocumentUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Update document metadata.

    Args:
        document_id: Document UUID
        data: Document update data

    Returns:
        Updated document
    """
    result = await db.execute(
        select(Document)
        .where(
            Document.id == document_id,
            Document.clinic_id == current_user.clinic_id,
        )
        .options(joinedload(Document.patient))
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    await db.commit()
    await db.refresh(document)

    # Add patient name
    doc_dict = DocumentResponse.model_validate(document).model_dump()
    doc_dict["patient_name"] = document.patient.full_name

    return DocumentResponse(**doc_dict)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Delete a document.

    Args:
        document_id: Document UUID
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.clinic_id == current_user.clinic_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete file from disk
    try:
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to delete file: {e}")

    # Delete record
    await db.delete(document)
    await db.commit()


# ========== Utility Endpoints ==========


@router.get("/types/available", response_model=DocumentTypeList)
async def get_document_types():
    """
    Get list of available document types.

    Returns:
        List of document type constants
    """
    return DocumentTypeList(types=DOCUMENT_TYPES)


@router.get("/stats/summary", response_model=DocumentStats)
async def get_document_stats(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get document statistics for the clinic.

    Returns:
        Document statistics
    """
    # Total documents
    total_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.clinic_id == current_user.clinic_id
        )
    )
    total = total_result.scalar() or 0

    # Processed count
    processed_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.clinic_id == current_user.clinic_id,
            Document.is_processed == True,
        )
    )
    processed = processed_result.scalar() or 0

    # By type
    type_result = await db.execute(
        select(Document.document_type, func.count(Document.id))
        .where(Document.clinic_id == current_user.clinic_id)
        .group_by(Document.document_type)
    )
    by_type = {
        doc_type or "other": count for doc_type, count in type_result.all()
    }

    # Total size
    size_result = await db.execute(
        select(func.sum(Document.file_size)).where(
            Document.clinic_id == current_user.clinic_id
        )
    )
    total_size_bytes = size_result.scalar() or 0
    total_size_mb = round(total_size_bytes / 1024 / 1024, 2)

    return DocumentStats(
        total=total,
        by_type=by_type,
        processed=processed,
        unprocessed=total - processed,
        total_size_mb=total_size_mb,
    )


@router.get("/patient/{patient_id}/summary", response_model=PatientDocumentSummary)
async def get_patient_document_summary(
    patient_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get document summary for a patient.

    Args:
        patient_id: Patient UUID

    Returns:
        Patient document summary
    """
    # Verify patient
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == current_user.clinic_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Total documents
    total_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.patient_id == patient_id,
            Document.clinic_id == current_user.clinic_id,
        )
    )
    total = total_result.scalar() or 0

    # By type
    type_result = await db.execute(
        select(Document.document_type, func.count(Document.id))
        .where(
            Document.patient_id == patient_id,
            Document.clinic_id == current_user.clinic_id,
        )
        .group_by(Document.document_type)
    )
    by_type = {
        doc_type or "other": count for doc_type, count in type_result.all()
    }

    # Latest document date
    latest_result = await db.execute(
        select(func.max(Document.scan_date)).where(
            Document.patient_id == patient_id,
            Document.clinic_id == current_user.clinic_id,
        )
    )
    latest_date = latest_result.scalar()

    return PatientDocumentSummary(
        patient_id=patient_id,
        patient_name=patient.full_name,
        total_documents=total,
        by_type=by_type,
        latest_document_date=latest_date,
    )
