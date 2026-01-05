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
    ActionChatRequest,
    ActionChatResponse,
    ActionPreview,
    ChatMessageRequest,
    ChatMessageResponse,
    ConfirmActionRequest,
    ConfirmActionResponse,
    MessageModel,
    SessionClearResponse,
    SessionHistoryResponse,
    UndoActionRequest,
    UndoActionResponse,
)
from app.schemas.insights import (
    DailyDigest,
    InsightListResponse,
    ProactiveInsightResponse,
    UserDigestPreferencesResponse,
    UserDigestPreferencesUpdate,
)
from app.services.ai_action_executor import AIActionExecutor, ActionType
from app.services.ai_assistant import get_ai_assistant, PracticeAIAssistant
from app.services.ai_entity_extractor import EntityExtractor
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
    current_user: CurrentUser,
    session_id: str = Path(..., description="Session ID"),
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
    current_user: CurrentUser,
    session_id: str = Path(..., description="Session ID"),
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
# Phase 16b: Conversational Actions Endpoints
# ============================================================================

# In-memory pending actions store (use Redis in production)
_pending_actions: dict[str, dict] = {}


@router.post("/chat/action", response_model=ActionChatResponse)
async def chat_with_actions(
    request: ActionChatRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Send a message that may trigger an action.

    Unlike /chat which only answers queries, this endpoint can:
    - Book appointments ("Book Rajesh for tomorrow at 3pm")
    - Reschedule appointments ("Move that to 4pm")
    - Cancel appointments ("Cancel Mr. Gupta's appointment")
    - Add to waitlist ("Add Priya to waitlist, high priority")
    - Send reminders ("Send reminder to next patient")

    Actions requiring confirmation will return requires_confirmation=true
    with an action_preview containing details to confirm.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    try:
        # Initialize services
        action_executor = AIActionExecutor(db)
        entity_extractor = EntityExtractor(db)

        # Get context from request
        context = request.context or {}
        context_patient_id = context.get("patient_id")
        context_doctor_id = context.get("doctor_id")

        # Extract entities from message
        extracted_date = entity_extractor.extract_date(request.message)
        extracted_time = entity_extractor.extract_time(request.message)
        patient = await entity_extractor.extract_patient(
            request.message, clinic_id, context_patient_id
        )
        doctor = await entity_extractor.extract_doctor(
            request.message, clinic_id, context_doctor_id
        )
        urgency = entity_extractor.extract_urgency(request.message)
        reason = entity_extractor.extract_reason(request.message)

        # Determine action type from message
        message_lower = request.message.lower()
        action_type = None
        params = {}

        if any(word in message_lower for word in ["book", "schedule", "appointment for"]):
            action_type = ActionType.BOOK_APPOINTMENT
            if not patient:
                return ActionChatResponse(
                    response="I couldn't find that patient. Please specify the patient name or phone number.",
                    requires_confirmation=False,
                    suggestions=["Search for patient first", "Book for [patient name]"],
                    session_id=request.session_id or str(current_user.id),
                )
            if not extracted_date or not extracted_time:
                return ActionChatResponse(
                    response=f"I found {patient.full_name}. When would you like to book the appointment? Please specify date and time.",
                    requires_confirmation=False,
                    suggestions=["Tomorrow at 3pm", "Next Monday morning", "Today at 4:30pm"],
                    session_id=request.session_id or str(current_user.id),
                )
            params = {
                "patient_id": patient.id,
                "doctor_id": doctor.id if doctor else None,
                "date": extracted_date,
                "time": extracted_time,
                "reason": reason,
            }

        elif any(word in message_lower for word in ["reschedule", "move", "change time"]):
            action_type = ActionType.RESCHEDULE_APPOINTMENT
            # Would need appointment context
            return ActionChatResponse(
                response="To reschedule, please specify the appointment and new time. You can say 'Reschedule [patient name]'s appointment to [new time]'.",
                requires_confirmation=False,
                suggestions=["Show today's appointments", "Reschedule to tomorrow"],
                session_id=request.session_id or str(current_user.id),
            )

        elif any(word in message_lower for word in ["cancel", "remove appointment"]):
            action_type = ActionType.CANCEL_APPOINTMENT
            return ActionChatResponse(
                response="To cancel, please specify which appointment. You can say 'Cancel [patient name]'s appointment'.",
                requires_confirmation=False,
                suggestions=["Show today's appointments", "Cancel next appointment"],
                session_id=request.session_id or str(current_user.id),
            )

        elif any(word in message_lower for word in ["waitlist", "waiting list", "add to wait"]):
            action_type = ActionType.ADD_TO_WAITLIST
            if not patient:
                return ActionChatResponse(
                    response="Which patient would you like to add to the waitlist?",
                    requires_confirmation=False,
                    suggestions=["Search for patient", "Add [patient name] to waitlist"],
                    session_id=request.session_id or str(current_user.id),
                )
            params = {
                "patient_id": patient.id,
                "doctor_id": doctor.id if doctor else None,
                "urgency": urgency,
                "notes": reason,
            }

        elif any(word in message_lower for word in ["remind", "send reminder", "notify"]):
            action_type = ActionType.SEND_REMINDER
            return ActionChatResponse(
                response="Which appointment would you like to send a reminder for?",
                requires_confirmation=False,
                suggestions=["Remind next patient", "Send all reminders for today"],
                session_id=request.session_id or str(current_user.id),
            )

        elif any(word in message_lower for word in ["find patient", "search patient", "look up", "lookup"]):
            action_type = ActionType.LOOKUP_PATIENT
            query = request.message.replace("find patient", "").replace("search patient", "").replace("look up", "").replace("lookup", "").strip()
            params = {"query": query}

        elif any(word in message_lower for word in ["availability", "available", "free slots", "open slots"]):
            action_type = ActionType.CHECK_AVAILABILITY
            params = {
                "date": extracted_date or __import__("datetime").date.today(),
                "doctor_id": doctor.id if doctor else None,
            }

        # If no action detected, fall back to query
        if not action_type:
            assistant = get_ai_assistant()
            response = await assistant.chat(
                message=request.message,
                clinic_id=clinic_id,
                user_id=current_user.id,
                session_id=request.session_id,
                context=request.context,
            )
            return ActionChatResponse(
                response=response.response,
                requires_confirmation=False,
                suggestions=response.suggestions,
                session_id=response.session_id,
            )

        # Check if action requires confirmation
        action_def = action_executor.ACTION_DEFINITIONS.get(action_type.value, {})
        requires_confirmation = action_def.get("requires_confirmation", False)

        if requires_confirmation:
            # Create pending action
            from uuid import uuid4
            from datetime import datetime, timedelta

            action_id = str(uuid4())
            expires_at = datetime.utcnow() + timedelta(minutes=5)

            # Build preview
            preview_data = {}
            if patient:
                preview_data["patient_name"] = patient.full_name
                preview_data["patient_phone"] = patient.phone
            if doctor:
                preview_data["doctor_name"] = doctor.full_name
            if extracted_date:
                preview_data["date"] = extracted_date.strftime("%d %b %Y")
            if extracted_time:
                preview_data["time"] = extracted_time.strftime("%I:%M %p")

            # Store pending action
            _pending_actions[action_id] = {
                "action_type": action_type,
                "params": params,
                "user_id": str(current_user.id),
                "clinic_id": str(clinic_id),
                "expires_at": expires_at,
            }

            # Build confirmation message
            if action_type == ActionType.BOOK_APPOINTMENT:
                confirm_msg = f"I'll book {patient.full_name} for {extracted_date.strftime('%d %b %Y')} at {extracted_time.strftime('%I:%M %p')}"
                if doctor:
                    confirm_msg += f" with Dr. {doctor.full_name}"
                confirm_msg += ". Confirm?"

            return ActionChatResponse(
                response=confirm_msg,
                requires_confirmation=True,
                action_preview=ActionPreview(
                    action_id=action_id,
                    action_type=action_type.value,
                    description=confirm_msg,
                    parameters=params,
                    preview_data=preview_data,
                    expires_at=expires_at,
                ),
                suggestions=["Yes, confirm", "No, cancel", "Change time"],
                session_id=request.session_id or str(current_user.id),
            )

        else:
            # Execute immediately (no confirmation needed)
            result = await action_executor.execute_action(
                action_type=action_type,
                params=params,
                user_id=current_user.id,
                clinic_id=clinic_id,
            )

            return ActionChatResponse(
                response=result.message,
                requires_confirmation=False,
                action_result=result.data,
                suggestions=["Book appointment", "Check availability", "Search patient"],
                session_id=request.session_id or str(current_user.id),
            )

    except Exception as e:
        logger.error(f"Action chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process action. Please try again.",
        )


@router.post("/chat/confirm", response_model=ConfirmActionResponse)
async def confirm_action(
    request: ConfirmActionRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Confirm or cancel a pending action.

    After receiving an action preview from /chat/action, use this endpoint
    to confirm (execute) or cancel the action.
    """
    from datetime import datetime

    # Get pending action
    pending = _pending_actions.get(request.action_id)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending action not found or expired",
        )

    # Verify ownership
    if pending["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to confirm this action",
        )

    # Check expiry
    if datetime.utcnow() > pending["expires_at"]:
        del _pending_actions[request.action_id]
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Action expired. Please try again.",
        )

    # Remove from pending
    del _pending_actions[request.action_id]

    if not request.confirmed:
        return ConfirmActionResponse(
            success=True,
            message="Action cancelled",
            action_type=pending["action_type"].value,
        )

    # Apply modifications if any
    params = pending["params"]
    if request.modifications:
        params.update(request.modifications)

    # Execute action
    action_executor = AIActionExecutor(db)
    result = await action_executor.execute_action(
        action_type=pending["action_type"],
        params=params,
        user_id=current_user.id,
        clinic_id=pending["clinic_id"],
    )

    return ConfirmActionResponse(
        success=result.success,
        message=result.message,
        action_type=pending["action_type"].value,
        action_data=result.data,
    )


@router.post("/chat/undo", response_model=UndoActionResponse)
async def undo_last_action(
    request: UndoActionRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Undo the last action.

    Supports undoing:
    - Book appointment (cancels)
    - Reschedule (restores original time)
    - Cancel (restores appointment)
    """
    try:
        action_executor = AIActionExecutor(db)
        result = await action_executor.undo_last_action(request.session_id)

        return UndoActionResponse(
            success=result.success,
            message=result.message,
            undone_action=result.action_type.value if result.success else None,
            restored_data=result.data,
        )

    except Exception as e:
        logger.error(f"Undo action error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to undo action",
        )


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
