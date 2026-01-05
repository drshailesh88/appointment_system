"""
Comprehensive tests for RAG Search Service.

Tests:
- Vector embedding generation
- Semantic search
- Hybrid search (semantic + keyword)
- Collection routing
- Graceful degradation when Qdrant unavailable
"""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag_search import (
    RAGSearchService,
    SearchCollection,
    SearchResult,
    SearchResponse,
)


# =====================================================================
# RAG Search Service Tests
# =====================================================================


class TestRAGSearchService:
    """Tests for RAG-Powered Search Service."""

    @pytest.fixture
    def service_with_mocks(self):
        """RAG service with mocked Qdrant and embedding."""
        service = RAGSearchService(qdrant_url=":memory:")

        # Mock Qdrant client
        mock_client = MagicMock()
        service._client = mock_client

        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [[0.1] * 384]  # 384-dim vector
        service._embedder = mock_embedder

        service._initialized = True

        return service

    @pytest.fixture
    def service_no_qdrant(self):
        """RAG service without Qdrant (fallback mode)."""
        with patch('app.services.rag_search.QDRANT_AVAILABLE', False):
            service = RAGSearchService()
            service._client = None
            service._embedder = None
            return service

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        return AsyncMock(spec=AsyncSession)

    # ===============================================================
    # Embedding Tests
    # ===============================================================

    def test_generate_embeddings(self, service_with_mocks):
        """Test embedding generation for text."""
        text = "Patient John Doe with phone +919876543210"

        embedding = service_with_mocks._embed(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384  # Standard embedding dimension

    def test_fallback_embeddings_when_fastembed_unavailable(self, service_no_qdrant):
        """Test hash-based fallback embeddings."""
        text = "Test patient"

        embedding = service_no_qdrant._embed(text)

        # Should generate 48 bytes from SHA384 (48 bytes * 8 bits = 384 bits)
        assert isinstance(embedding, list)
        assert len(embedding) == 48  # SHA384 produces 48 bytes

    # ===============================================================
    # Collection Management Tests
    # ===============================================================

    @pytest.mark.asyncio
    async def test_ensure_collection_creation(self, service_with_mocks):
        """Test collection is created if it doesn't exist."""
        service_with_mocks._client.get_collection.side_effect = Exception("Not found")

        await service_with_mocks._ensure_collection(SearchCollection.PATIENTS)

        # Should attempt to create collection
        service_with_mocks._client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_creates_all_collections(self, service_with_mocks, mock_db):
        """Test initialization creates all collections."""
        clinic_id = uuid4()

        # Mock get_collection to raise exception (doesn't exist)
        service_with_mocks._client.get_collection.side_effect = Exception("Not found")

        # Mock DB queries to return empty results
        mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: []))

        await service_with_mocks.initialize(clinic_id, mock_db)

        # Should create all 3 collections
        assert service_with_mocks._client.create_collection.call_count == 3

    # ===============================================================
    # Indexing Tests
    # ===============================================================

    @pytest.mark.asyncio
    async def test_index_patients(self, service_with_mocks, mock_db):
        """Test patient indexing."""
        clinic_id = uuid4()

        # Mock patients
        mock_patients = [
            MagicMock(
                id=uuid4(),
                full_name="John Doe",
                phone="+919876543210",
                email="john@example.com",
                gender="male",
                blood_group="O+",
                address="123 Main St"
            ),
            MagicMock(
                id=uuid4(),
                full_name="Jane Smith",
                phone="+919876543211",
                email="jane@example.com",
                gender="female",
                blood_group="A+",
                address="456 Oak Ave"
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_patients
        mock_db.execute.return_value = mock_result

        await service_with_mocks._index_patients(clinic_id, mock_db)

        # Should upsert points
        service_with_mocks._client.upsert.assert_called_once()
        call_args = service_with_mocks._client.upsert.call_args
        assert call_args[1]["collection_name"] == SearchCollection.PATIENTS.value
        assert len(call_args[1]["points"]) == 2

    @pytest.mark.asyncio
    async def test_index_doctors(self, service_with_mocks, mock_db):
        """Test doctor indexing."""
        clinic_id = uuid4()

        # Mock doctors
        mock_doctors = [
            MagicMock(
                id=uuid4(),
                name="Dr. Sharma",
                specialization="Cardiology",
                qualification="MBBS, MD",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_doctors
        mock_db.execute.return_value = mock_result

        await service_with_mocks._index_doctors(clinic_id, mock_db)

        service_with_mocks._client.upsert.assert_called_once()
        call_args = service_with_mocks._client.upsert.call_args
        assert call_args[1]["collection_name"] == SearchCollection.DOCTORS.value

    @pytest.mark.asyncio
    async def test_index_appointments(self, service_with_mocks, mock_db):
        """Test appointment indexing (only last 90 days)."""
        clinic_id = uuid4()

        # Mock appointments
        mock_appointments = [
            MagicMock(
                id=uuid4(),
                patient_id=uuid4(),
                doctor_id=uuid4(),
                scheduled_start=datetime.now() - timedelta(days=30),
                status="completed",
                chief_complaint="Fever and cough",
                notes="Patient recovering well"
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_appointments
        mock_db.execute.return_value = mock_result

        await service_with_mocks._index_appointments(clinic_id, mock_db)

        service_with_mocks._client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_single_patient(self, service_with_mocks):
        """Test indexing a single patient."""
        clinic_id = uuid4()
        mock_patient = MagicMock(
            id=uuid4(),
            full_name="Test Patient",
            phone="+919999999999",
            email="test@example.com",
        )

        await service_with_mocks.index_patient(mock_patient, clinic_id)

        service_with_mocks._client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_from_index(self, service_with_mocks):
        """Test deleting an item from the index."""
        item_id = str(uuid4())

        await service_with_mocks.delete_from_index(item_id, SearchCollection.PATIENTS)

        service_with_mocks._client.delete.assert_called_once()

    # ===============================================================
    # Search Tests
    # ===============================================================

    @pytest.mark.asyncio
    async def test_semantic_search(self, service_with_mocks):
        """Test semantic search across collections."""
        clinic_id = uuid4()

        # Mock search results
        mock_results = [
            MagicMock(
                id=str(uuid4()),
                score=0.95,
                payload={
                    "clinic_id": str(clinic_id),
                    "name": "John Doe",
                    "phone": "+919876543210",
                    "text": "Patient: John Doe | Phone: +919876543210"
                }
            ),
            MagicMock(
                id=str(uuid4()),
                score=0.88,
                payload={
                    "clinic_id": str(clinic_id),
                    "name": "Jane Doe",
                    "phone": "+919876543211",
                    "text": "Patient: Jane Doe | Phone: +919876543211"
                }
            ),
        ]

        service_with_mocks._client.search.return_value = mock_results

        response = await service_with_mocks.search(
            query="Find patient Doe",
            clinic_id=clinic_id,
            limit=10
        )

        assert isinstance(response, SearchResponse)
        assert len(response.results) > 0
        assert response.results[0].score >= response.results[-1].score  # Sorted by score

    @pytest.mark.asyncio
    async def test_search_specific_collection(self, service_with_mocks):
        """Test searching in a specific collection only."""
        clinic_id = uuid4()

        service_with_mocks._client.search.return_value = []

        response = await service_with_mocks.search(
            query="Dr. Sharma",
            clinic_id=clinic_id,
            collections=[SearchCollection.DOCTORS],
            limit=5
        )

        assert isinstance(response, SearchResponse)
        # Should only search doctors collection
        service_with_mocks._client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_routing(self, service_with_mocks):
        """Test automatic query routing based on keywords."""
        # Patient query
        patient_query = "find patient with phone 9876543210"
        routed = service_with_mocks._route_query(
            patient_query,
            list(SearchCollection)
        )
        assert SearchCollection.PATIENTS in routed

        # Doctor query
        doctor_query = "cardiologist specialist"
        routed = service_with_mocks._route_query(
            doctor_query,
            list(SearchCollection)
        )
        assert SearchCollection.DOCTORS in routed

        # Appointment query
        appt_query = "appointment booking for tomorrow"
        routed = service_with_mocks._route_query(
            appt_query,
            list(SearchCollection)
        )
        assert SearchCollection.APPOINTMENTS in routed

        # Ambiguous query (should search all)
        ambiguous_query = "find records"
        routed = service_with_mocks._route_query(
            ambiguous_query,
            list(SearchCollection)
        )
        assert len(routed) == 3  # All collections

    @pytest.mark.asyncio
    async def test_hybrid_search_with_filters(self, service_with_mocks):
        """Test hybrid search with additional filters."""
        clinic_id = uuid4()

        service_with_mocks._client.search.return_value = []

        response = await service_with_mocks.search(
            query="patient",
            clinic_id=clinic_id,
            filters={"blood_group": "O+"},
            limit=10
        )

        # Should apply filters in Qdrant query
        assert isinstance(response, SearchResponse)

    @pytest.mark.asyncio
    async def test_search_returns_empty_gracefully(self, service_with_mocks):
        """Test handling empty search results."""
        clinic_id = uuid4()

        service_with_mocks._client.search.return_value = []

        response = await service_with_mocks.search(
            query="nonexistent patient xyz123",
            clinic_id=clinic_id,
        )

        assert response.total_count == 0
        assert len(response.results) == 0

    @pytest.mark.asyncio
    async def test_search_error_handling(self, service_with_mocks):
        """Test error handling during search."""
        clinic_id = uuid4()

        service_with_mocks._client.search.side_effect = Exception("Qdrant error")

        response = await service_with_mocks.search(
            query="test",
            clinic_id=clinic_id,
        )

        # Should return empty results instead of crashing
        assert response.total_count == 0

    # ===============================================================
    # Fallback Mode Tests (No Qdrant)
    # ===============================================================

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_qdrant_unavailable(self, service_no_qdrant):
        """Test service operates in fallback mode when Qdrant unavailable."""
        clinic_id = uuid4()

        response = await service_no_qdrant.search(
            query="test patient",
            clinic_id=clinic_id,
        )

        # Should return empty results but not crash
        assert isinstance(response, SearchResponse)
        assert response.total_count == 0

    @pytest.mark.asyncio
    async def test_fallback_search_implementation(self, service_no_qdrant):
        """Test fallback search when Qdrant not available."""
        results = service_no_qdrant._fallback_search(
            query="test",
            collection=SearchCollection.PATIENTS,
            clinic_id=uuid4(),
            limit=10
        )

        # Fallback returns empty list (could be enhanced with SQL-based search)
        assert isinstance(results, list)
        assert len(results) == 0

    # ===============================================================
    # Text Conversion Tests
    # ===============================================================

    def test_patient_to_text_conversion(self, service_with_mocks):
        """Test converting patient to searchable text."""
        mock_patient = MagicMock(
            full_name="John Doe",
            phone="+919876543210",
            email="john@example.com",
            gender="male",
            blood_group="O+",
            address="123 Main St"
        )

        text = service_with_mocks._patient_to_text(mock_patient)

        assert "John Doe" in text
        assert "+919876543210" in text
        assert "john@example.com" in text
        assert "O+" in text

    def test_doctor_to_text_conversion(self, service_with_mocks):
        """Test converting doctor to searchable text."""
        mock_doctor = MagicMock(
            name="Sharma",
            specialization="Cardiology",
            qualification="MBBS, MD"
        )

        text = service_with_mocks._doctor_to_text(mock_doctor)

        assert "Sharma" in text
        assert "Cardiology" in text
        assert "MBBS" in text

    def test_appointment_to_text_conversion(self, service_with_mocks):
        """Test converting appointment to searchable text."""
        mock_appointment = MagicMock(
            scheduled_start=datetime(2024, 3, 15, 10, 0),
            status="completed",
            chief_complaint="Fever and headache",
            notes="Prescribed medication"
        )

        text = service_with_mocks._appointment_to_text(mock_appointment)

        assert "2024-03-15" in text
        assert "completed" in text
        assert "Fever and headache" in text
        assert "Prescribed medication" in text

    # ===============================================================
    # Performance Tests
    # ===============================================================

    @pytest.mark.asyncio
    async def test_search_performance_tracking(self, service_with_mocks):
        """Test that search time is tracked."""
        clinic_id = uuid4()

        service_with_mocks._client.search.return_value = []

        response = await service_with_mocks.search(
            query="test",
            clinic_id=clinic_id,
        )

        assert response.search_time_ms >= 0
        assert isinstance(response.search_time_ms, float)

    @pytest.mark.asyncio
    async def test_batch_indexing_performance(self, service_with_mocks, mock_db):
        """Test indexing large batch of patients."""
        clinic_id = uuid4()

        # Mock large patient list
        mock_patients = [
            MagicMock(
                id=uuid4(),
                full_name=f"Patient {i}",
                phone=f"+9198765432{i:02d}",
                email=f"patient{i}@example.com",
                gender="male",
                blood_group="O+",
                address="Test Address"
            )
            for i in range(100)
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_patients
        mock_db.execute.return_value = mock_result

        await service_with_mocks._index_patients(clinic_id, mock_db)

        # Should successfully index all patients
        service_with_mocks._client.upsert.assert_called_once()
        call_args = service_with_mocks._client.upsert.call_args
        assert len(call_args[1]["points"]) == 100


# =====================================================================
# Integration Tests
# =====================================================================


class TestRAGIntegration:
    """Integration tests for RAG search."""

    @pytest.fixture
    def service_in_memory(self):
        """RAG service with in-memory Qdrant."""
        try:
            from qdrant_client import QdrantClient

            service = RAGSearchService(qdrant_url=":memory:")
            service._init_client()
            service._init_embedder()
            return service
        except ImportError:
            pytest.skip("Qdrant not installed")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_patient_search(self, service_in_memory, mock_db):
        """Test end-to-end patient indexing and search."""
        clinic_id = uuid4()

        # Create and index patients
        mock_patients = [
            MagicMock(
                id=uuid4(),
                full_name="John Smith",
                phone="+919876543210",
                email="john@example.com",
                gender="male",
                blood_group="O+",
                address="Mumbai"
            ),
            MagicMock(
                id=uuid4(),
                full_name="Jane Doe",
                phone="+919876543211",
                email="jane@example.com",
                gender="female",
                blood_group="A+",
                address="Delhi"
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_patients
        mock_db.execute.return_value = mock_result

        await service_in_memory._index_patients(clinic_id, mock_db)

        # Search for patient
        response = await service_in_memory.search(
            query="patient John Smith",
            clinic_id=clinic_id,
            collections=[SearchCollection.PATIENTS],
            limit=5
        )

        assert response.total_count > 0
        # First result should be John Smith (semantic match)
        assert "John" in response.results[0].text or "Smith" in response.results[0].text
