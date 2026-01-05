"""
Natural Language Analytics API endpoints.

Phase 16A: Natural Language Analytics

Provides dedicated endpoints for natural language analytics queries
with real data integration (not mocked).

Endpoints:
- POST /ai/analytics/query - Execute NL analytics query
- GET /ai/analytics/suggestions - Get suggested queries
- GET /ai/analytics/health - Check NL analytics service health
"""

import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.schemas.ai_analytics import (
    NLAnalyticsHealthResponse,
    NLQueryRequest,
    NLQueryResponse,
    QuerySuggestion,
    QuerySuggestionsResponse,
)
from app.services.ai_assistant import get_ai_assistant, PracticeAIAssistant
from app.services.nl_analytics import get_nl_analytics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analytics/query", response_model=NLQueryResponse)
async def execute_nl_query(
    request: NLQueryRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Execute a natural language analytics query.

    Supports queries like:
    - **Procedures:** "How many echos this month?", "Top procedures by revenue"
    - **Revenue:** "Revenue today", "Collection rate this week"
    - **Appointments:** "Appointment stats today", "No-show rate this month"
    - **Patients:** "Find diabetic patients", "Search by phone"
    - **Doctors:** "Dr. Sharma's stats", "Top performing doctor"

    Returns natural language response with structured data for visualization.

    **Example:**
    ```json
    {
        "query": "How many procedures did we do this month?"
    }
    ```

    **Response:**
    ```json
    {
        "answer": "This month you've completed 127 procedures:\\n\\n• Cardiology: 68 (54%)...",
        "data": {"total": 127, "by_category": {...}},
        "visualization_type": "bar_chart",
        "suggestions": ["Breakdown by doctor", "Compare to last month"]
    }
    ```
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    start_time = time.time()

    try:
        # Get AI assistant
        assistant = get_ai_assistant()

        # Parse query using AI
        function_call = await assistant._parse_query(
            message=request.query,
            session=assistant._sessions.get(
                request.session_id or "",
                None,
            )
            or assistant._sessions.setdefault(
                request.session_id or str(current_user.id),
                assistant.__class__.__dict__["ConversationSession"](
                    session_id=request.session_id or str(current_user.id),
                    user_id=str(current_user.id),
                    clinic_id=str(clinic_id),
                ),
            ),
            context=request.context,
        )

        if not function_call:
            # No function identified
            return NLQueryResponse(
                answer="I'm not sure what you're asking. Try queries like 'How many procedures this month?' or 'Revenue today'.",
                data={},
                visualization_type=None,
                suggestions=[
                    "How many procedures this month?",
                    "Revenue today",
                    "Appointment stats this week",
                    "No-show rate this month",
                ],
                session_id=request.session_id or str(current_user.id),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Execute query with real analytics
        nl_analytics = get_nl_analytics(db)
        result = await nl_analytics.execute_query(
            function_call=function_call,
            clinic_id=clinic_id,
        )

        processing_time = (time.time() - start_time) * 1000

        return NLQueryResponse(
            answer=result.natural_response,
            data=result.structured_data,
            visualization_type=result.visualization_type,
            sql_generated=result.sql_generated if settings.debug else None,
            suggestions=result.suggestions,
            session_id=request.session_id or str(current_user.id),
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"NL analytics query error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}",
        )


@router.get("/analytics/suggestions", response_model=QuerySuggestionsResponse)
async def get_query_suggestions(
    current_user: CurrentUser,
    db: DbSession,
    category: Optional[str] = None,
):
    """
    Get suggested analytics queries.

    Returns context-aware suggestions based on clinic activity.

    **Query Parameters:**
    - `category`: Optional filter by category (revenue, appointments, procedures, patients, doctors)

    **Example Response:**
    ```json
    {
        "suggestions": [
            {
                "query": "Revenue today",
                "category": "revenue",
                "icon": "currency-rupee",
                "description": "Shows today's revenue and collection"
            },
            {
                "query": "How many procedures this month?",
                "category": "procedures",
                "icon": "medical-bag",
                "description": "Procedure count and breakdown"
            }
        ],
        "categories": ["revenue", "appointments", "procedures", "patients", "doctors"]
    }
    ```
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    try:
        # Get context-aware suggestions
        nl_analytics = get_nl_analytics(db)
        raw_suggestions = await nl_analytics.get_query_suggestions(clinic_id)

        # Convert to structured suggestions with categories
        suggestions = []

        # Revenue suggestions
        revenue_queries = [
            ("Revenue today", "Shows today's revenue and collection"),
            ("Revenue this month", "Monthly revenue summary"),
            ("Collection rate this week", "Payment collection efficiency"),
            ("Outstanding payments", "Pending invoices and amounts"),
        ]

        # Appointments suggestions
        appointment_queries = [
            ("Appointments today", "Today's appointment count"),
            ("Appointment stats this week", "Weekly appointment breakdown"),
            ("No-show rate this month", "Patient no-show analysis"),
            ("Cancellation rate", "Appointment cancellation trends"),
        ]

        # Procedures suggestions
        procedure_queries = [
            ("How many procedures this month?", "Procedure count and categories"),
            ("Top procedures by revenue", "Highest earning procedures"),
            ("Procedure trends", "Procedure volume over time"),
        ]

        # Patients suggestions
        patient_queries = [
            ("Find patient", "Search by name, phone, or condition"),
            ("New patients this month", "Recently registered patients"),
        ]

        # Doctors suggestions
        doctor_queries = [
            ("Doctor performance this month", "Doctor-wise statistics"),
            ("Dr. Sharma's stats", "Individual doctor metrics"),
            ("Top performing doctor", "Highest productivity"),
        ]

        # Build suggestion list
        all_suggestions = [
            (revenue_queries, "revenue", "currency-rupee"),
            (appointment_queries, "appointments", "calendar"),
            (procedure_queries, "procedures", "medical-bag"),
            (patient_queries, "patients", "users"),
            (doctor_queries, "doctors", "user-md"),
        ]

        for queries, cat, icon in all_suggestions:
            if category and category != cat:
                continue

            for query_text, description in queries:
                if query_text in raw_suggestions or not category:
                    suggestions.append(
                        QuerySuggestion(
                            query=query_text,
                            category=cat,
                            icon=icon,
                            description=description,
                        )
                    )

        categories = ["revenue", "appointments", "procedures", "patients", "doctors"]

        return QuerySuggestionsResponse(
            suggestions=suggestions,
            categories=categories,
        )

    except Exception as e:
        logger.error(f"Get suggestions error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch suggestions",
        )


@router.get("/analytics/health", response_model=NLAnalyticsHealthResponse)
async def check_analytics_health(
    current_user: CurrentUser,
):
    """
    Check natural language analytics service health.

    Verifies:
    - Ollama API accessibility
    - LLM model availability
    - Service status

    **Example Response:**
    ```json
    {
        "status": "healthy",
        "ollama_available": true,
        "model": "qwen2.5:3b",
        "last_query_time": "2026-01-05T10:30:00Z"
    }
    ```
    """
    import httpx
    from datetime import datetime

    try:
        # Check Ollama availability
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_available = response.status_code == 200

        if not ollama_available:
            return NLAnalyticsHealthResponse(
                status="degraded",
                ollama_available=False,
                model=settings.ollama_model,
                error="Ollama API not accessible",
            )

        # Check if model is available
        models_response = await client.get(f"{settings.ollama_base_url}/api/tags")
        models = models_response.json().get("models", [])
        model_available = any(
            settings.ollama_model in m.get("name", "") for m in models
        )

        if not model_available:
            return NLAnalyticsHealthResponse(
                status="degraded",
                ollama_available=True,
                model=settings.ollama_model,
                error=f"Model {settings.ollama_model} not found",
            )

        return NLAnalyticsHealthResponse(
            status="healthy",
            ollama_available=True,
            model=settings.ollama_model,
            last_query_time=datetime.utcnow(),
        )

    except httpx.HTTPError as e:
        logger.error(f"Ollama health check failed: {e}")
        return NLAnalyticsHealthResponse(
            status="unhealthy",
            ollama_available=False,
            model=settings.ollama_model,
            error=f"Ollama connection error: {str(e)}",
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return NLAnalyticsHealthResponse(
            status="unhealthy",
            ollama_available=False,
            model=settings.ollama_model,
            error=str(e),
        )
