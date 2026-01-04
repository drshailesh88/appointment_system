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
