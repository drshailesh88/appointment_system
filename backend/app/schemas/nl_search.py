"""
Natural Language Search schemas.

Schemas for NL-powered appointment search requests and responses.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NLSearchRequest(BaseModel):
    """Natural language search request."""

    query: str = Field(..., min_length=1, max_length=500, description="Natural language query")
    context: dict[str, Any] | None = Field(
        None,
        description="Optional context (e.g., current date range filter, doctor filter)",
    )


class ParsedDateFilter(BaseModel):
    """Parsed date filter from query."""

    start_date: date | None = None
    end_date: date | None = None
    exact_date: date | None = None
    relative_description: str | None = None  # e.g., "tomorrow", "next week"


class ParsedQuery(BaseModel):
    """Structured interpretation of natural language query."""

    entities: dict[str, Any] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)
    query_type: str = Field(..., description="Type of query: search, aggregate, status")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in parsing")
    parsed_date: ParsedDateFilter | None = None
    patient_name: str | None = None
    doctor_name: str | None = None
    status_filter: list[str] | None = None
    appointment_type: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None


class AppointmentSearchResult(BaseModel):
    """Single appointment search result."""

    id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    scheduled_start: datetime
    duration_minutes: int
    status: str
    appointment_type: str
    chief_complaint: str | None
    token_number: int | None
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    match_reason: str | None = Field(None, description="Why this result matched")


class AggregateData(BaseModel):
    """Aggregate query result data."""

    count: int
    breakdown: dict[str, int] | None = None
    trend_data: list[dict[str, Any]] | None = None


class AggregateResponse(BaseModel):
    """Response for aggregate queries."""

    answer: str = Field(..., description="Natural language answer")
    data: AggregateData
    visualization_hint: str | None = Field(
        None,
        description="Suggestion for visualization (chart_type: bar, line, pie)",
    )
    query: str


class SearchSuggestion(BaseModel):
    """Query suggestion."""

    text: str
    category: str  # time, patient, status, doctor
    icon: str | None = None


class NLSearchResponse(BaseModel):
    """Natural language search response."""

    results: list[AppointmentSearchResult]
    summary: str = Field(..., description="Natural language summary of results")
    suggestions: list[SearchSuggestion] = Field(
        default_factory=list,
        description="Follow-up query suggestions",
    )
    parsed_query: ParsedQuery
    total_count: int
    search_time_ms: float


class SearchHistoryEntry(BaseModel):
    """Search history entry."""

    id: str
    query: str
    timestamp: datetime
    result_count: int
    category: str


class SearchHistoryResponse(BaseModel):
    """Search history response."""

    entries: list[SearchHistoryEntry]
    total_count: int


class ParseQueryRequest(BaseModel):
    """Request to parse a query without executing search."""

    query: str = Field(..., min_length=1, max_length=500)


class ParseQueryResponse(BaseModel):
    """Response from query parsing."""

    parsed_query: ParsedQuery
    suggested_refinements: list[str] = Field(
        default_factory=list,
        description="Suggestions to make query more specific",
    )
