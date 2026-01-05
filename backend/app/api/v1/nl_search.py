"""
Natural Language Appointment Search API endpoints.

AI-powered conversational search for appointments.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.nl_search import (
    AggregateResponse,
    NLSearchRequest,
    NLSearchResponse,
    ParseQueryRequest,
    ParseQueryResponse,
    SearchHistoryResponse,
    SearchSuggestion,
)
from app.services.nl_appointment_search import (
    NLAppointmentSearchService,
    get_nl_search_service,
)

router = APIRouter()


@router.post("/appointments", response_model=NLSearchResponse)
async def natural_language_search(
    request: NLSearchRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Search appointments using natural language queries.

    **Examples:**
    - "appointments tomorrow"
    - "this week's schedule"
    - "Dr. Sharma's appointments next Monday"
    - "cancelled appointments this month"
    - "Rajesh Kumar's pending appointments"
    - "no-shows last week"
    - "emergency appointments today"

    **Supports:**
    - Relative dates (tomorrow, next week, last Monday)
    - Patient/doctor name search
    - Status filters (cancelled, confirmed, pending, etc.)
    - Appointment types (emergency, follow-up, etc.)
    - Mixed Hindi/English queries
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_nl_search_service()

    try:
        result = await service.search(
            query=request.query,
            clinic_id=clinic_id,
            db=db,
            context=request.context,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post("/parse", response_model=ParseQueryResponse)
async def parse_query(
    request: ParseQueryRequest,
    current_user: CurrentUser,
):
    """
    Parse a natural language query without executing the search.

    Useful for showing users how their query is interpreted
    and providing real-time parsing feedback.
    """
    service = get_nl_search_service()

    try:
        parsed_query = await service.parse_query(
            query=request.query,
            context=None,
        )

        # Generate suggested refinements
        suggestions = []
        if parsed_query.confidence < 0.7:
            suggestions.append("Try being more specific with dates or names")

        if not parsed_query.parsed_date:
            suggestions.append("Add a time frame (e.g., 'tomorrow', 'this week')")

        if parsed_query.needs_clarification:
            suggestions.append(parsed_query.clarification_question or "Please provide more details")

        return ParseQueryResponse(
            parsed_query=parsed_query,
            suggested_refinements=suggestions,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query parsing failed: {str(e)}",
        )


@router.get("/suggestions", response_model=list[SearchSuggestion])
async def get_search_suggestions(
    current_user: CurrentUser,
):
    """
    Get suggested search queries based on common use cases.

    Returns pre-defined query suggestions to help users
    discover the natural language search capabilities.
    """
    service = get_nl_search_service()

    return service.get_suggestions()


@router.post("/aggregate", response_model=AggregateResponse)
async def aggregate_query(
    request: NLSearchRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Execute aggregate queries (counts, statistics).

    **Examples:**
    - "how many appointments tomorrow"
    - "number of no-shows this month"
    - "total appointments this week"
    - "count of cancelled appointments today"
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_nl_search_service()

    try:
        result = await service.aggregate_query(
            query=request.query,
            clinic_id=clinic_id,
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Aggregate query failed: {str(e)}",
        )


@router.get("/history", response_model=SearchHistoryResponse)
async def get_search_history(
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100, description="Number of history entries"),
):
    """
    Get recent search history for the current user's clinic.

    Returns the most recent natural language searches
    performed by users in this clinic.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_nl_search_service()

    history = service.get_search_history(clinic_id, limit=limit)

    return SearchHistoryResponse(
        entries=history,
        total_count=len(history),
    )
