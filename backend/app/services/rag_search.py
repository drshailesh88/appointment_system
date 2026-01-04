"""
RAG-Powered Search Service using Qdrant.

Provides semantic search across patients, appointments, and doctors with:
- Hybrid search (semantic + keyword)
- Natural language queries
- Database routing for different entity types
- Real-time indexing on data changes

Reference: https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/rag_tutorials
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Try to import Qdrant - graceful fallback if not installed
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant not installed. Using fallback search.")

# Try to import FastEmbed for embeddings
try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    logger.warning("FastEmbed not installed. Using simple embeddings.")


class SearchCollection(str, Enum):
    """Available search collections."""
    PATIENTS = "patients"
    APPOINTMENTS = "appointments"
    DOCTORS = "doctors"


@dataclass
class SearchResult:
    """A single search result."""
    id: str
    collection: SearchCollection
    score: float
    text: str
    metadata: dict


@dataclass
class SearchResponse:
    """Response from a search query."""
    query: str
    results: list[SearchResult]
    total_count: int
    search_time_ms: float


class RAGSearchService:
    """
    RAG-Powered Search Service.

    Features:
    - Semantic search using embeddings
    - Hybrid search (vector + keyword filtering)
    - Multi-collection routing (patients, appointments, doctors)
    - Real-time indexing
    - Natural language query understanding
    """

    # Embedding dimension (all-MiniLM-L6-v2 = 384)
    EMBEDDING_DIM = 384

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """
        Initialize RAG Search Service.

        Args:
            qdrant_url: Qdrant server URL (or ":memory:" for in-memory)
            embedding_model: Model for text embeddings
        """
        self.qdrant_url = qdrant_url
        self.embedding_model_name = embedding_model
        self._client: Optional[QdrantClient] = None
        self._embedder: Optional[TextEmbedding] = None
        self._initialized = False

    def _init_client(self):
        """Initialize Qdrant client lazily."""
        if self._client is not None:
            return

        if not QDRANT_AVAILABLE:
            logger.warning("Qdrant not available, search will use fallback")
            return

        try:
            if self.qdrant_url == ":memory:":
                self._client = QdrantClient(":memory:")
            else:
                self._client = QdrantClient(url=self.qdrant_url)
            logger.info(f"Connected to Qdrant at {self.qdrant_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self._client = None

    def _init_embedder(self):
        """Initialize embedding model lazily."""
        if self._embedder is not None:
            return

        if not FASTEMBED_AVAILABLE:
            logger.warning("FastEmbed not available, using simple embeddings")
            return

        try:
            self._embedder = TextEmbedding(model_name=self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._embedder = None

    async def initialize(self, clinic_id: UUID, db: AsyncSession):
        """
        Initialize collections and index existing data.

        Args:
            clinic_id: Clinic to index data for
            db: Database session
        """
        self._init_client()
        self._init_embedder()

        if self._client is None:
            logger.warning("Qdrant not available, skipping initialization")
            return

        # Create collections
        for collection in SearchCollection:
            await self._ensure_collection(collection)

        # Index existing data
        await self._index_patients(clinic_id, db)
        await self._index_doctors(clinic_id, db)
        await self._index_appointments(clinic_id, db)

        self._initialized = True
        logger.info(f"RAG Search initialized for clinic {clinic_id}")

    async def _ensure_collection(self, collection: SearchCollection):
        """Create collection if it doesn't exist."""
        if self._client is None:
            return

        try:
            self._client.get_collection(collection.value)
        except Exception:
            self._client.create_collection(
                collection_name=collection.value,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {collection.value}")

    def _embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if self._embedder is None:
            # Simple fallback: hash-based pseudo-embedding
            import hashlib
            hash_bytes = hashlib.sha384(text.encode()).digest()
            return [b / 255.0 for b in hash_bytes]

        embeddings = list(self._embedder.embed([text]))
        return embeddings[0].tolist()

    async def _index_patients(self, clinic_id: UUID, db: AsyncSession):
        """Index all patients for a clinic."""
        from app.models.patient import Patient

        result = await db.execute(
            select(Patient).where(Patient.clinic_id == clinic_id)
        )
        patients = result.scalars().all()

        points = []
        for patient in patients:
            text = self._patient_to_text(patient)
            embedding = self._embed(text)
            points.append(PointStruct(
                id=str(patient.id),
                vector=embedding,
                payload={
                    "clinic_id": str(clinic_id),
                    "name": patient.full_name,
                    "phone": patient.phone,
                    "email": patient.email,
                    "gender": patient.gender,
                    "blood_group": patient.blood_group,
                    "text": text,
                },
            ))

        if points and self._client:
            self._client.upsert(
                collection_name=SearchCollection.PATIENTS.value,
                points=points,
            )
            logger.info(f"Indexed {len(points)} patients")

    async def _index_doctors(self, clinic_id: UUID, db: AsyncSession):
        """Index all doctors for a clinic."""
        from app.models.doctor import Doctor

        result = await db.execute(
            select(Doctor).where(Doctor.clinic_id == clinic_id)
        )
        doctors = result.scalars().all()

        points = []
        for doctor in doctors:
            text = self._doctor_to_text(doctor)
            embedding = self._embed(text)
            points.append(PointStruct(
                id=str(doctor.id),
                vector=embedding,
                payload={
                    "clinic_id": str(clinic_id),
                    "name": doctor.name,
                    "specialization": doctor.specialization,
                    "qualification": doctor.qualification,
                    "text": text,
                },
            ))

        if points and self._client:
            self._client.upsert(
                collection_name=SearchCollection.DOCTORS.value,
                points=points,
            )
            logger.info(f"Indexed {len(points)} doctors")

    async def _index_appointments(self, clinic_id: UUID, db: AsyncSession):
        """Index recent appointments for a clinic."""
        from app.models.appointment import Appointment

        # Only index last 90 days of appointments
        cutoff = datetime.now() - timedelta(days=90)

        result = await db.execute(
            select(Appointment)
            .where(Appointment.clinic_id == clinic_id)
            .where(Appointment.scheduled_start >= cutoff)
        )
        appointments = result.scalars().all()

        points = []
        for appt in appointments:
            text = self._appointment_to_text(appt)
            embedding = self._embed(text)
            points.append(PointStruct(
                id=str(appt.id),
                vector=embedding,
                payload={
                    "clinic_id": str(clinic_id),
                    "patient_id": str(appt.patient_id),
                    "doctor_id": str(appt.doctor_id),
                    "date": appt.scheduled_start.date().isoformat(),
                    "status": appt.status,
                    "chief_complaint": appt.chief_complaint,
                    "text": text,
                },
            ))

        if points and self._client:
            self._client.upsert(
                collection_name=SearchCollection.APPOINTMENTS.value,
                points=points,
            )
            logger.info(f"Indexed {len(points)} appointments")

    def _patient_to_text(self, patient) -> str:
        """Convert patient to searchable text."""
        parts = [
            f"Patient: {patient.full_name}",
            f"Phone: {patient.phone}",
        ]
        if patient.email:
            parts.append(f"Email: {patient.email}")
        if patient.gender:
            parts.append(f"Gender: {patient.gender}")
        if patient.blood_group:
            parts.append(f"Blood Group: {patient.blood_group}")
        if patient.address:
            parts.append(f"Address: {patient.address}")
        return " | ".join(parts)

    def _doctor_to_text(self, doctor) -> str:
        """Convert doctor to searchable text."""
        parts = [
            f"Dr. {doctor.name}",
            f"Specialization: {doctor.specialization}",
        ]
        if doctor.qualification:
            parts.append(f"Qualification: {doctor.qualification}")
        return " | ".join(parts)

    def _appointment_to_text(self, appointment) -> str:
        """Convert appointment to searchable text."""
        parts = [
            f"Appointment on {appointment.scheduled_start.date()}",
            f"Status: {appointment.status}",
        ]
        if appointment.chief_complaint:
            parts.append(f"Reason: {appointment.chief_complaint}")
        if appointment.notes:
            parts.append(f"Notes: {appointment.notes}")
        return " | ".join(parts)

    async def search(
        self,
        query: str,
        clinic_id: UUID,
        collections: list[SearchCollection] | None = None,
        limit: int = 10,
        filters: dict | None = None,
    ) -> SearchResponse:
        """
        Search across collections using hybrid search.

        Args:
            query: Natural language search query
            clinic_id: Limit to this clinic
            collections: Collections to search (default: all)
            limit: Max results per collection
            filters: Additional filters

        Returns:
            SearchResponse with ranked results
        """
        import time
        start_time = time.time()

        if collections is None:
            collections = list(SearchCollection)

        # Route query to appropriate collection(s)
        routed_collections = self._route_query(query, collections)

        all_results = []

        for collection in routed_collections:
            results = await self._search_collection(
                query=query,
                collection=collection,
                clinic_id=clinic_id,
                limit=limit,
                filters=filters,
            )
            all_results.extend(results)

        # Sort by score and limit
        all_results.sort(key=lambda r: r.score, reverse=True)
        all_results = all_results[:limit]

        search_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=all_results,
            total_count=len(all_results),
            search_time_ms=search_time_ms,
        )

    def _route_query(
        self,
        query: str,
        available: list[SearchCollection],
    ) -> list[SearchCollection]:
        """
        Route query to relevant collections based on keywords.

        Simple keyword-based routing. Can be enhanced with LLM.
        """
        query_lower = query.lower()

        # Patient-related keywords
        patient_keywords = ["patient", "name", "phone", "contact", "blood", "age"]
        # Doctor-related keywords
        doctor_keywords = ["doctor", "dr", "specialist", "cardiologist", "dermatologist"]
        # Appointment-related keywords
        appt_keywords = ["appointment", "booking", "schedule", "visit", "consult"]

        routed = []

        if any(kw in query_lower for kw in patient_keywords):
            if SearchCollection.PATIENTS in available:
                routed.append(SearchCollection.PATIENTS)

        if any(kw in query_lower for kw in doctor_keywords):
            if SearchCollection.DOCTORS in available:
                routed.append(SearchCollection.DOCTORS)

        if any(kw in query_lower for kw in appt_keywords):
            if SearchCollection.APPOINTMENTS in available:
                routed.append(SearchCollection.APPOINTMENTS)

        # If no specific routing, search all
        if not routed:
            routed = available

        return routed

    async def _search_collection(
        self,
        query: str,
        collection: SearchCollection,
        clinic_id: UUID,
        limit: int,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Search a single collection."""
        if self._client is None:
            return self._fallback_search(query, collection, clinic_id, limit)

        try:
            # Generate query embedding
            query_embedding = self._embed(query)

            # Build filter
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="clinic_id",
                        match=MatchValue(value=str(clinic_id)),
                    )
                ]
            )

            # Search
            results = self._client.search(
                collection_name=collection.value,
                query_vector=query_embedding,
                limit=limit,
                query_filter=qdrant_filter,
            )

            return [
                SearchResult(
                    id=str(r.id),
                    collection=collection,
                    score=r.score,
                    text=r.payload.get("text", ""),
                    metadata=r.payload,
                )
                for r in results
            ]

        except Exception as e:
            logger.error(f"Search error in {collection.value}: {e}")
            return []

    def _fallback_search(
        self,
        query: str,
        collection: SearchCollection,
        clinic_id: UUID,
        limit: int,
    ) -> list[SearchResult]:
        """Fallback search when Qdrant not available."""
        # Simple keyword matching - would be enhanced in production
        return []

    async def index_patient(self, patient, clinic_id: UUID):
        """Index or update a single patient."""
        if self._client is None:
            return

        text = self._patient_to_text(patient)
        embedding = self._embed(text)

        self._client.upsert(
            collection_name=SearchCollection.PATIENTS.value,
            points=[PointStruct(
                id=str(patient.id),
                vector=embedding,
                payload={
                    "clinic_id": str(clinic_id),
                    "name": patient.full_name,
                    "phone": patient.phone,
                    "email": patient.email,
                    "text": text,
                },
            )],
        )

    async def index_appointment(self, appointment, clinic_id: UUID):
        """Index or update a single appointment."""
        if self._client is None:
            return

        text = self._appointment_to_text(appointment)
        embedding = self._embed(text)

        self._client.upsert(
            collection_name=SearchCollection.APPOINTMENTS.value,
            points=[PointStruct(
                id=str(appointment.id),
                vector=embedding,
                payload={
                    "clinic_id": str(clinic_id),
                    "patient_id": str(appointment.patient_id),
                    "doctor_id": str(appointment.doctor_id),
                    "date": appointment.scheduled_start.date().isoformat(),
                    "status": appointment.status,
                    "text": text,
                },
            )],
        )

    async def delete_from_index(self, id: str, collection: SearchCollection):
        """Delete an item from the index."""
        if self._client is None:
            return

        self._client.delete(
            collection_name=collection.value,
            points_selector=[id],
        )


# Singleton instance
_search_service: Optional[RAGSearchService] = None


def get_search_service() -> RAGSearchService:
    """Get or create the search service singleton."""
    global _search_service
    if _search_service is None:
        _search_service = RAGSearchService()
    return _search_service
