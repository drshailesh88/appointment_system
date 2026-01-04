"""
Tests for RAG Search Service.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

from app.services.rag_search import (
    RAGSearchService,
    SearchCollection,
    SearchResult,
    SearchResponse,
    get_search_service,
)


class TestSearchCollection:
    """Tests for SearchCollection enum."""

    def test_all_collections_exist(self):
        """Test all expected collections exist."""
        assert SearchCollection.PATIENTS == "patients"
        assert SearchCollection.APPOINTMENTS == "appointments"
        assert SearchCollection.DOCTORS == "doctors"


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_result(self):
        """Test creating a search result."""
        result = SearchResult(
            id="123",
            collection=SearchCollection.PATIENTS,
            score=0.95,
            text="Patient: John Doe",
            metadata={"name": "John Doe"},
        )
        assert result.id == "123"
        assert result.collection == SearchCollection.PATIENTS
        assert result.score == 0.95


class TestSearchResponse:
    """Tests for SearchResponse dataclass."""

    def test_create_response(self):
        """Test creating a search response."""
        results = [
            SearchResult(
                id="1",
                collection=SearchCollection.PATIENTS,
                score=0.9,
                text="Patient A",
                metadata={},
            ),
        ]
        response = SearchResponse(
            query="find patient",
            results=results,
            total_count=1,
            search_time_ms=5.5,
        )
        assert response.query == "find patient"
        assert len(response.results) == 1
        assert response.search_time_ms == 5.5


class TestRAGSearchService:
    """Tests for RAGSearchService."""

    def test_initialization(self):
        """Test service initialization."""
        service = RAGSearchService(qdrant_url=":memory:")
        assert service.qdrant_url == ":memory:"
        assert service._client is None
        assert service._embedder is None

    def test_embed_fallback(self):
        """Test embedding fallback when FastEmbed not available."""
        service = RAGSearchService()
        service._embedder = None

        # Should use hash-based fallback
        embedding = service._embed("test text")
        assert len(embedding) == 48  # SHA384 = 48 bytes
        assert all(0 <= v <= 1 for v in embedding)

    def test_route_query_patients(self):
        """Test query routing to patients collection."""
        service = RAGSearchService()
        collections = list(SearchCollection)

        # Patient keywords
        result = service._route_query("find patient John", collections)
        assert SearchCollection.PATIENTS in result

    def test_route_query_doctors(self):
        """Test query routing to doctors collection."""
        service = RAGSearchService()
        collections = list(SearchCollection)

        # Doctor keywords
        result = service._route_query("Dr. Sharma specialist", collections)
        assert SearchCollection.DOCTORS in result

    def test_route_query_appointments(self):
        """Test query routing to appointments collection."""
        service = RAGSearchService()
        collections = list(SearchCollection)

        # Appointment keywords
        result = service._route_query("schedule appointment tomorrow", collections)
        assert SearchCollection.APPOINTMENTS in result

    def test_route_query_all(self):
        """Test query routing when no specific keywords."""
        service = RAGSearchService()
        collections = list(SearchCollection)

        # No specific keywords - should return all
        result = service._route_query("search for something", collections)
        assert len(result) == len(collections)

    def test_patient_to_text(self):
        """Test patient to text conversion."""
        service = RAGSearchService()

        # Create mock patient
        patient = MagicMock()
        patient.full_name = "John Doe"
        patient.phone = "+919876543210"
        patient.email = "john@example.com"
        patient.gender = "male"
        patient.blood_group = "O+"
        patient.address = "123 Main St"

        text = service._patient_to_text(patient)

        assert "John Doe" in text
        assert "+919876543210" in text
        assert "john@example.com" in text
        assert "O+" in text

    def test_doctor_to_text(self):
        """Test doctor to text conversion."""
        service = RAGSearchService()

        doctor = MagicMock()
        doctor.name = "Sharma"
        doctor.specialization = "Cardiology"
        doctor.qualification = "MBBS, MD"

        text = service._doctor_to_text(doctor)

        assert "Sharma" in text
        assert "Cardiology" in text
        assert "MBBS" in text

    def test_appointment_to_text(self):
        """Test appointment to text conversion."""
        from datetime import datetime

        service = RAGSearchService()

        appointment = MagicMock()
        appointment.scheduled_start = datetime(2025, 1, 15, 10, 0)
        appointment.status = "scheduled"
        appointment.chief_complaint = "Headache"
        appointment.notes = None

        text = service._appointment_to_text(appointment)

        assert "2025-01-15" in text
        assert "scheduled" in text
        assert "Headache" in text


class TestGetSearchService:
    """Tests for search service singleton."""

    def test_singleton(self):
        """Test that get_search_service returns same instance."""
        # Reset singleton
        import app.services.rag_search as module
        module._search_service = None

        service1 = get_search_service()
        service2 = get_search_service()

        assert service1 is service2


class TestRAGSearchIntegration:
    """Integration tests for RAG search (with mocked Qdrant)."""

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no results."""
        service = RAGSearchService()
        clinic_id = uuid4()

        response = await service.search(
            query="nonexistent patient",
            clinic_id=clinic_id,
        )

        assert response.query == "nonexistent patient"
        assert response.total_count == 0
        assert len(response.results) == 0

    @pytest.mark.asyncio
    async def test_search_with_collections_filter(self):
        """Test search with specific collections."""
        service = RAGSearchService()
        clinic_id = uuid4()

        response = await service.search(
            query="test",
            clinic_id=clinic_id,
            collections=[SearchCollection.PATIENTS],
            limit=5,
        )

        assert response.query == "test"

    @pytest.mark.asyncio
    async def test_index_patient(self):
        """Test indexing a single patient."""
        service = RAGSearchService()
        clinic_id = uuid4()

        patient = MagicMock()
        patient.id = uuid4()
        patient.full_name = "Test Patient"
        patient.phone = "+919999999999"
        patient.email = None
        patient.gender = None
        patient.blood_group = None
        patient.address = None

        # Should not raise even without Qdrant
        await service.index_patient(patient, clinic_id)

    @pytest.mark.asyncio
    async def test_index_appointment(self):
        """Test indexing a single appointment."""
        from datetime import datetime

        service = RAGSearchService()
        clinic_id = uuid4()

        appointment = MagicMock()
        appointment.id = uuid4()
        appointment.patient_id = uuid4()
        appointment.doctor_id = uuid4()
        appointment.scheduled_start = datetime.now()
        appointment.status = "scheduled"
        appointment.chief_complaint = "Test"
        appointment.notes = None

        # Should not raise even without Qdrant
        await service.index_appointment(appointment, clinic_id)
