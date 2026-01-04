"""
AI Chat API endpoints.

Phase 16a: Practice AI Assistant - Natural Language Analytics

Endpoints:
- POST /ai/chat - Send message to AI assistant
- GET /ai/sessions/{session_id} - Get conversation history
- DELETE /ai/sessions/{session_id} - Clear session
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.schemas.ai_chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    MessageModel,
    SessionClearResponse,
    SessionHistoryResponse,
)
from app.services.ai_assistant import get_ai_assistant, PracticeAIAssistant

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
