"""
AI Chat API endpoints.

Phase 16a: Practice AI Assistant - Natural Language Analytics
Phase 16c: Proactive Intelligence

Endpoints:
- POST /ai/chat - Send message to AI assistant
- GET /ai/sessions/{session_id} - Get conversation history
- DELETE /ai/sessions/{session_id} - Clear session
- GET /ai/insights - Get proactive insights
- GET /ai/insights/digest - Get daily digest
- POST /ai/insights/{insight_id}/dismiss - Dismiss an insight
- POST /ai/insights/{insight_id}/act - Act on an insight
- GET /ai/preferences/digest - Get digest preferences
- PUT /ai/preferences/digest - Update digest preferences
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.schemas.ai_chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    MessageModel,
    SessionClearResponse,
    SessionHistoryResponse,
)
from app.schemas.insights import (
    DailyDigest,
    InsightListResponse,
    ProactiveInsightResponse,
    UserDigestPreferencesResponse,
    UserDigestPreferencesUpdate,
)
from app.services.ai_assistant import get_ai_assistant, PracticeAIAssistant
from app.services.daily_digest import DailyDigestService
from app.services.proactive_insights import ProactiveInsightsEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Send a message to the AI assistant.

    The AI will parse the message, determine the appropriate analytics function,
    execute it, and return a natural language response with follow-up suggestions.

    **Example queries:**
    - "How many procedures this month?"
    - "Revenue last week"
    - "Dr. Sharma's procedure count"
    - "Find diabetic patients"
    - "No-show rate this month"
    - "Compare revenue this month vs last month"
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    try:
        # Get AI assistant
        assistant = get_ai_assistant()

        # Process message
        response = await assistant.chat(
            message=request.message,
            clinic_id=clinic_id,
            user_id=current_user.id,
            session_id=request.session_id,
            context=request.context,
        )

        return ChatMessageResponse(
            response=response.response,
            suggestions=response.suggestions,
            data=response.data,
            function_called=response.function_called,
            session_id=response.session_id,
        )

    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message. Please try again.",
        )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str = Path(..., description="Session ID"),
    current_user: CurrentUser = Depends(),
):
    """
    Get conversation history for a session.

    Returns all messages in the session with timestamps.
    """
    assistant = get_ai_assistant()
    session = assistant.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Verify user owns this session
    if session.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    return SessionHistoryResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        clinic_id=session.clinic_id,
        messages=[
            MessageModel(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
            )
            for msg in session.messages
        ],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/sessions/{session_id}", response_model=SessionClearResponse)
async def clear_session(
    session_id: str = Path(..., description="Session ID"),
    current_user: CurrentUser = Depends(),
):
    """
    Clear a conversation session.

    This removes all message history and context for the session.
    """
    assistant = get_ai_assistant()

    # Verify session exists and user owns it
    session = assistant.get_session(session_id)
    if session and session.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to clear this session",
        )

    success = assistant.clear_session(session_id)

    if success:
        return SessionClearResponse(
            success=True,
            message="Session cleared successfully",
        )
    else:
        return SessionClearResponse(
            success=False,
            message="Session not found",
        )


@router.post("/sessions/cleanup")
async def cleanup_old_sessions(
    current_user: CurrentUser,
    max_age_hours: int = 24,
):
    """
    Cleanup old sessions (admin only).

    Removes sessions older than max_age_hours.
    """
    # Only clinic admins can cleanup
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can cleanup sessions",
        )

    assistant = get_ai_assistant()
    assistant.cleanup_old_sessions(max_age_hours=max_age_hours)

    return {"message": f"Cleaned up sessions older than {max_age_hours} hours"}


# ============================================================================
# Phase 16c: Proactive Intelligence Endpoints
# ============================================================================


@router.get("/insights", response_model=InsightListResponse)
async def get_insights(
    current_user: CurrentUser,
    db: DbSession,
    insight_types: Optional[list[str]] = Query(None, description="Filter by insight types"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of insights"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """
    Get current proactive insights.

    Returns active (not dismissed/expired) insights for the clinic.

    **Insight Types:**
    - followup_due
    - schedule_gap
    - revenue_alert
    - no_show_risk
    - waitlist_opportunity
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    try:
        engine = ProactiveInsightsEngine(db)
        insights = await engine.get_active_insights(
            clinic_id=clinic_id,
            insight_types=insight_types,
            limit=limit,
        )

        return InsightListResponse(
            insights=insights,
            total=len(insights),
            page=page,
            page_size=limit,
        )

    except Exception as e:
        logger.error(f"Get insights error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch insights",
        )


@router.get("/insights/digest", response_model=DailyDigest)
async def get_daily_digest(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get today's daily digest.

    Returns personalized digest with:
    - Appointments today
    - Revenue yesterday
    - Pending follow-ups
    - Schedule alerts
    - Waitlist opportunities
    - Key insights
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    try:
        digest_service = DailyDigestService(db)
        digest = await digest_service.generate_digest(
            clinic_id=clinic_id,
            user_id=current_user.id,
        )

        return digest

    except Exception as e:
        logger.error(f"Get digest error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate digest",
        )


@router.post("/insights/{insight_id}/dismiss")
async def dismiss_insight(
    insight_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Dismiss an insight.

    Marks the insight as dismissed so it won't appear again.
    """
    try:
        engine = ProactiveInsightsEngine(db)
        insight = await engine.dismiss_insight(
            insight_id=insight_id,
            user_id=current_user.id,
        )

        return {
            "success": True,
            "message": "Insight dismissed successfully",
            "insight": insight,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Dismiss insight error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dismiss insight",
        )


@router.post("/insights/{insight_id}/act")
async def act_on_insight(
    insight_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Act on an insight.

    Marks the insight as acted upon (one-click action executed).
    """
    try:
        engine = ProactiveInsightsEngine(db)
        insight = await engine.act_on_insight(
            insight_id=insight_id,
            user_id=current_user.id,
        )

        return {
            "success": True,
            "message": "Action recorded successfully",
            "insight": insight,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Act on insight error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record action",
        )


@router.get("/preferences/digest", response_model=UserDigestPreferencesResponse)
async def get_digest_preferences(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get user's digest preferences.

    Returns delivery time, channels, and content filters.
    """
    try:
        digest_service = DailyDigestService(db)
        prefs = await digest_service.get_user_preferences(current_user.id)

        if not prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preferences not found. Use PUT to create.",
            )

        return UserDigestPreferencesResponse.model_validate(prefs)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get digest preferences error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch preferences",
        )


@router.put("/preferences/digest", response_model=UserDigestPreferencesResponse)
async def update_digest_preferences(
    preferences: UserDigestPreferencesUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Update digest preferences.

    Creates preferences if they don't exist.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    try:
        digest_service = DailyDigestService(db)

        # Get update dict (only non-None values)
        update_data = preferences.model_dump(exclude_unset=True)

        prefs = await digest_service.create_or_update_preferences(
            user_id=current_user.id,
            clinic_id=clinic_id,
            **update_data,
        )

        return UserDigestPreferencesResponse.model_validate(prefs)

    except Exception as e:
        logger.error(f"Update digest preferences error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )
