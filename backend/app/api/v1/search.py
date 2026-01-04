"""
RAG-Powered Search API endpoints.

Natural language search across patients, appointments, and doctors.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.services.rag_search import (
    RAGSearchService,
    SearchCollection,
    SearchResponse,
    get_search_service,
)

router = APIRouter()


class SearchResultModel(BaseModel):
    """API model for a search result."""
    id: str
    collection: str
    score: float
    text: str
    metadata: dict


class SearchResponseModel(BaseModel):
    """API response model for search."""
    query: str
    results: list[SearchResultModel]
    total_count: int
    search_time_ms: float


class IndexStatusModel(BaseModel):
    """Status of the search index."""
    initialized: bool
    collections: list[str]
    patient_count: int
    doctor_count: int
    appointment_count: int


@router.get("/", response_model=SearchResponseModel)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    db: DbSession = None,
    current_user: CurrentUser = None,
    collections: Optional[str] = Query(
        None,
        description="Comma-separated collection names (patients,appointments,doctors)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
):
    """
    Search across patients, appointments, and doctors.

    Uses semantic search with natural language understanding.

    Examples:
    - "patients with blood group O+"
    - "appointments scheduled for tomorrow"
    - "Dr. Sharma's availability"
    - "John's phone number"
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Parse collections
    search_collections = None
    if collections:
        try:
            search_collections = [
                SearchCollection(c.strip())
                for c in collections.split(",")
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid collection: {e}",
            )

    # Perform search
    service = get_search_service()
    response = await service.search(
        query=q,
        clinic_id=clinic_id,
        collections=search_collections,
        limit=limit,
    )

    return SearchResponseModel(
        query=response.query,
        results=[
            SearchResultModel(
                id=r.id,
                collection=r.collection.value,
                score=r.score,
                text=r.text,
                metadata=r.metadata,
            )
            for r in response.results
        ],
        total_count=response.total_count,
        search_time_ms=response.search_time_ms,
    )


@router.post("/initialize")
async def initialize_search_index(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Initialize or rebuild the search index for the current clinic.

    This will index all patients, doctors, and appointments.
    """
    if current_user.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can initialize search index",
        )

    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_search_service()
    await service.initialize(clinic_id, db)

    return {"message": "Search index initialized", "clinic_id": str(clinic_id)}


@router.get("/status", response_model=IndexStatusModel)
async def get_index_status(
    current_user: CurrentUser,
):
    """Get the status of the search index."""
    service = get_search_service()

    # Get collection stats
    collections = [c.value for c in SearchCollection]

    # In a real implementation, we'd query Qdrant for counts
    return IndexStatusModel(
        initialized=service._initialized,
        collections=collections,
        patient_count=0,  # Would be fetched from Qdrant
        doctor_count=0,
        appointment_count=0,
    )


@router.post("/patients/{patient_id}")
async def index_patient(
    patient_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Index or re-index a specific patient."""
    from app.models.patient import Patient

    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get patient
    patient = await db.get(Patient, patient_id)
    if not patient or patient.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    service = get_search_service()
    await service.index_patient(patient, clinic_id)

    return {"message": "Patient indexed", "patient_id": str(patient_id)}


@router.post("/appointments/{appointment_id}")
async def index_appointment(
    appointment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Index or re-index a specific appointment."""
    from app.models.appointment import Appointment

    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get appointment
    appointment = await db.get(Appointment, appointment_id)
    if not appointment or appointment.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    service = get_search_service()
    await service.index_appointment(appointment, clinic_id)

    return {"message": "Appointment indexed", "appointment_id": str(appointment_id)}
