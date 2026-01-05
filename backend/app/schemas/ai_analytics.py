"""
Pydantic schemas for Natural Language Analytics API.

Phase 16A: Natural Language Analytics
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class NLQueryRequest(BaseModel):
    """Request for natural language analytics query."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language query (e.g., 'How many echos this month?')",
        examples=[
            "How many procedures this month?",
            "Revenue today",
            "No-show rate this week",
            "Find diabetic patients",
            "Dr. Sharma's stats",
        ],
    )
    context: Optional[dict[str, Any]] = Field(
        None,
        description="Optional context (selected doctor, date range, etc.)",
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation continuity",
    )


class NLQueryResponse(BaseModel):
    """Response from natural language analytics query."""

    answer: str = Field(
        ...,
        description="Natural language answer to the query",
    )
    data: Optional[dict[str, Any]] = Field(
        None,
        description="Structured data for visualization (charts, tables)",
    )
    visualization_type: Optional[str] = Field(
        None,
        description="Suggested visualization type: bar_chart, line_chart, donut_chart, table, metric",
    )
    sql_generated: Optional[str] = Field(
        None,
        description="Generated SQL query (for debugging, only in dev mode)",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Follow-up query suggestions",
    )
    session_id: str = Field(
        ...,
        description="Session ID for follow-up queries",
    )
    processing_time_ms: Optional[float] = Field(
        None,
        description="Query processing time in milliseconds",
    )


class QuerySuggestion(BaseModel):
    """A suggested query with category."""

    query: str = Field(..., description="The suggested query text")
    category: str = Field(
        ...,
        description="Category: revenue, appointments, procedures, patients, doctors",
    )
    icon: Optional[str] = Field(
        None,
        description="Icon name for UI display",
    )
    description: Optional[str] = Field(
        None,
        description="Brief description of what the query returns",
    )


class QuerySuggestionsResponse(BaseModel):
    """Response containing suggested queries."""

    suggestions: list[QuerySuggestion] = Field(
        ...,
        description="List of suggested queries",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Available query categories",
    )


class NLAnalyticsHealthResponse(BaseModel):
    """Health check response for NL analytics."""

    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    ollama_available: bool = Field(..., description="Whether Ollama is accessible")
    model: str = Field(..., description="LLM model being used")
    last_query_time: Optional[datetime] = Field(
        None,
        description="Timestamp of last successful query",
    )
    error: Optional[str] = Field(None, description="Error message if unhealthy")


# Export for backward compatibility with existing ai_chat schemas
class AnalyticsQueryRequest(NLQueryRequest):
    """Alias for backward compatibility."""

    pass


class AnalyticsQueryResponse(NLQueryResponse):
    """Alias for backward compatibility."""

    pass
