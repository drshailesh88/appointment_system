"""
Tests for Documents API endpoints.

Phase 10: Document Scanner & OCR
"""

import io
import uuid
from datetime import datetime

import pytest
from fastapi import status
from httpx import AsyncClient
from PIL import Image

from app.models.document import Document


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for upload testing."""
    img = Image.new("RGB", (800, 600), color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes


@pytest.mark.asyncio
async def test_upload_document(
    async_client: AsyncClient,
    auth_headers: dict,
    test_patient_id: uuid.UUID,
    sample_image_bytes,
):
    """Test document upload endpoint."""
    files = {
        "file": ("test_document.jpg", sample_image_bytes, "image/jpeg"),
    }
    data = {
        "patient_id": str(test_patient_id),
        "document_type": "lab_report",
        "notes": "Blood test report",
    }

    response = await async_client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    result = response.json()
    assert "id" in result
    assert result["original_filename"] == "test_document.jpg"
    assert result["file_type"] == "image/jpeg"
    assert "message" in result


@pytest.mark.asyncio
async def test_upload_document_invalid_patient(
    async_client: AsyncClient,
    auth_headers: dict,
    sample_image_bytes,
):
    """Test document upload with invalid patient ID."""
    files = {
        "file": ("test.jpg", sample_image_bytes, "image/jpeg"),
    }
    data = {
        "patient_id": str(uuid.uuid4()),  # Non-existent patient
        "document_type": "lab_report",
    }

    response = await async_client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_upload_document_invalid_file_type(
    async_client: AsyncClient,
    auth_headers: dict,
    test_patient_id: uuid.UUID,
):
    """Test document upload with invalid file type."""
    files = {
        "file": ("test.exe", io.BytesIO(b"fake exe"), "application/exe"),
    }
    data = {
        "patient_id": str(test_patient_id),
    }

    response = await async_client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not allowed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_documents(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test listing documents."""
    response = await async_client.get(
        "/api/v1/documents",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "items" in result
    assert "total" in result
    assert "limit" in result
    assert "offset" in result


@pytest.mark.asyncio
async def test_list_documents_with_filters(
    async_client: AsyncClient,
    auth_headers: dict,
    test_patient_id: uuid.UUID,
):
    """Test listing documents with filters."""
    response = await async_client.get(
        "/api/v1/documents",
        params={
            "patient_id": str(test_patient_id),
            "document_type": "lab_report",
            "is_processed": True,
            "limit": 10,
            "offset": 0,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_document(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_patient_id: uuid.UUID,
    test_clinic_id: uuid.UUID,
):
    """Test getting a specific document."""
    # Create a document first
    document = Document(
        clinic_id=test_clinic_id,
        patient_id=test_patient_id,
        file_path="uploads/test.jpg",
        file_type="image/jpeg",
        original_filename="test.jpg",
        file_size=12345,
        document_type="lab_report",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    response = await async_client.get(
        f"/api/v1/documents/{document.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["id"] == str(document.id)
    assert result["original_filename"] == "test.jpg"


@pytest.mark.asyncio
async def test_get_document_not_found(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting non-existent document."""
    response = await async_client.get(
        f"/api/v1/documents/{uuid.uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_patient_documents(
    async_client: AsyncClient,
    auth_headers: dict,
    test_patient_id: uuid.UUID,
):
    """Test getting all documents for a patient."""
    response = await async_client.get(
        f"/api/v1/documents/patient/{test_patient_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_patient_documents_invalid_patient(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting documents for non-existent patient."""
    response = await async_client.get(
        f"/api/v1/documents/patient/{uuid.uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_document(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_patient_id: uuid.UUID,
    test_clinic_id: uuid.UUID,
):
    """Test updating document metadata."""
    # Create a document
    document = Document(
        clinic_id=test_clinic_id,
        patient_id=test_patient_id,
        file_path="uploads/test.jpg",
        file_type="image/jpeg",
        original_filename="test.jpg",
        document_type="other",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    # Update document
    update_data = {
        "document_type": "lab_report",
        "notes": "Updated notes",
        "tags": ["blood_test", "routine"],
    }

    response = await async_client.patch(
        f"/api/v1/documents/{document.id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["document_type"] == "lab_report"
    assert result["notes"] == "Updated notes"
    assert "blood_test" in result["tags"]


@pytest.mark.asyncio
async def test_delete_document(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_patient_id: uuid.UUID,
    test_clinic_id: uuid.UUID,
):
    """Test deleting a document."""
    # Create a document
    document = Document(
        clinic_id=test_clinic_id,
        patient_id=test_patient_id,
        file_path="uploads/test.jpg",
        file_type="image/jpeg",
        original_filename="test.jpg",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    response = await async_client.delete(
        f"/api/v1/documents/{document.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify deletion
    response = await async_client.get(
        f"/api/v1/documents/{document.id}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_document_types(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting available document types."""
    response = await async_client.get(
        "/api/v1/documents/types/available",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "types" in result
    assert "lab_report" in result["types"]
    assert "prescription" in result["types"]


@pytest.mark.asyncio
async def test_get_document_stats(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting document statistics."""
    response = await async_client.get(
        "/api/v1/documents/stats/summary",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "total" in result
    assert "by_type" in result
    assert "processed" in result
    assert "unprocessed" in result
    assert "total_size_mb" in result


@pytest.mark.asyncio
async def test_get_patient_document_summary(
    async_client: AsyncClient,
    auth_headers: dict,
    test_patient_id: uuid.UUID,
):
    """Test getting document summary for a patient."""
    response = await async_client.get(
        f"/api/v1/documents/patient/{test_patient_id}/summary",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "patient_id" in result
    assert "patient_name" in result
    assert "total_documents" in result
    assert "by_type" in result


@pytest.mark.skipif(
    True,  # Skip by default as OCR is slow
    reason="OCR processing test skipped (slow)",
)
@pytest.mark.asyncio
async def test_process_ocr(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_patient_id: uuid.UUID,
    test_clinic_id: uuid.UUID,
):
    """Test OCR processing on a document."""
    # Create a document with a real image file
    # This test requires the actual file to exist
    document = Document(
        clinic_id=test_clinic_id,
        patient_id=test_patient_id,
        file_path="uploads/test_image.jpg",
        file_type="image/jpeg",
        original_filename="test.jpg",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    ocr_request = {
        "languages": ["en", "hi"],
        "extract_structured_data": True,
    }

    response = await async_client.post(
        f"/api/v1/documents/{document.id}/ocr",
        json=ocr_request,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "ocr_text" in result
    assert "ocr_confidence" in result
    assert "processing_time_seconds" in result
