"""
Pydantic schemas for AI Chat API.

Phase 16a: Practice AI Assistant
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""

    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for context continuation")
    context: Optional[dict[str, Any]] = Field(
        None,
        description="Optional UI context (current screen, selected patient, etc.)",
    )


class ChatMessageResponse(BaseModel):
    """Response from AI assistant."""

    response: str = Field(..., description="Natural language response from AI")
    suggestions: list[str] = Field(
        default_factory=list,
        description="Follow-up question suggestions",
    )
    data: Optional[dict[str, Any]] = Field(
        None,
        description="Structured data for UI rendering (charts, tables)",
    )
    function_called: Optional[str] = Field(
        None,
        description="Name of the function that was executed",
    )
    session_id: str = Field(..., description="Session ID for future messages")


class MessageModel(BaseModel):
    """A single message in conversation history."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="When the message was sent")


class SessionHistoryResponse(BaseModel):
    """Conversation session history."""

    session_id: str
    user_id: str
    clinic_id: str
    messages: list[MessageModel]
    created_at: datetime
    updated_at: datetime


class SessionClearResponse(BaseModel):
    """Response after clearing a session."""

    success: bool
    message: str


# ============================================================================
# Phase 16b: Conversational Actions Schemas
# ============================================================================


class ActionPreview(BaseModel):
    """Preview of an action before confirmation."""

    action_id: str = Field(..., description="Unique ID for this pending action")
    action_type: str = Field(..., description="Type of action (book_appointment, etc.)")
    description: str = Field(..., description="Human-readable action description")
    parameters: dict[str, Any] = Field(..., description="Action parameters")
    preview_data: Optional[dict[str, Any]] = Field(
        None,
        description="Preview data for UI display (patient name, time, etc.)",
    )
    expires_at: datetime = Field(..., description="When this pending action expires")


class ActionChatRequest(BaseModel):
    """Request for action-based chat (booking, rescheduling, etc.)."""

    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    context: Optional[dict[str, Any]] = Field(
        None,
        description="Optional context (current patient, screen, etc.)",
    )


class ActionChatResponse(BaseModel):
    """Response that may include an action to confirm."""

    response: str = Field(..., description="Natural language response")
    requires_confirmation: bool = Field(
        default=False,
        description="Whether user must confirm an action",
    )
    action_preview: Optional[ActionPreview] = Field(
        None,
        description="Preview of pending action (if requires_confirmation)",
    )
    action_result: Optional[dict[str, Any]] = Field(
        None,
        description="Result of executed action (if no confirmation needed)",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Follow-up suggestions",
    )
    session_id: str = Field(..., description="Session ID")


class ConfirmActionRequest(BaseModel):
    """Request to confirm or cancel a pending action."""

    action_id: str = Field(..., description="ID of the pending action")
    confirmed: bool = Field(..., description="True to confirm, False to cancel")
    modifications: Optional[dict[str, Any]] = Field(
        None,
        description="Optional modifications before confirming",
    )


class ConfirmActionResponse(BaseModel):
    """Response after confirming/canceling an action."""

    success: bool
    message: str
    action_type: Optional[str] = None
    action_data: Optional[dict[str, Any]] = None


class UndoActionRequest(BaseModel):
    """Request to undo the last action."""

    session_id: str = Field(..., description="Session ID")


class UndoActionResponse(BaseModel):
    """Response after undo attempt."""

    success: bool
    message: str
    undone_action: Optional[str] = Field(None, description="Type of action that was undone")
    restored_data: Optional[dict[str, Any]] = Field(
        None,
        description="Data about the restored state",
    )
