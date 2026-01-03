"""
Voice Agent API endpoints.
"""

import base64
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.voice.agent import VoiceAgent, VoiceResponse

router = APIRouter()

# Global voice agent instance
_voice_agent: Optional[VoiceAgent] = None


def get_voice_agent() -> VoiceAgent:
    """Get or create voice agent singleton."""
    global _voice_agent
    if _voice_agent is None:
        _voice_agent = VoiceAgent()
    return _voice_agent


class TextInput(BaseModel):
    """Text input for voice agent (testing)."""

    text: str
    session_id: Optional[str] = None
    clinic_id: UUID


class VoiceResponseModel(BaseModel):
    """Voice response model."""

    text: str
    audio_base64: Optional[str] = None
    state: str
    booking_complete: bool
    appointment_id: Optional[UUID] = None
    next_action: Optional[str] = None
    session_id: str
    metadata: dict = {}


@router.post("/process-audio", response_model=VoiceResponseModel)
async def process_audio(
    db: DbSession,
    current_user: CurrentUser,
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = None,
    clinic_id: Optional[UUID] = None,
):
    """
    Process audio input for voice booking.

    Upload audio file (WAV, MP3, etc.) and get voice response.
    """
    if not clinic_id:
        clinic_id = current_user.clinic_id
        if not clinic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="clinic_id is required",
            )

    if not session_id:
        session_id = str(uuid4())

    # Read audio data
    audio_data = await audio_file.read()

    # Process with voice agent
    agent = get_voice_agent()
    response = await agent.process_audio(
        audio_data=audio_data,
        session_id=session_id,
        clinic_id=clinic_id,
        db=db,
    )

    return _format_response(response, session_id)


@router.post("/process-text", response_model=VoiceResponseModel)
async def process_text(
    db: DbSession,
    current_user: CurrentUser,
    input_data: TextInput,
):
    """
    Process text input for voice booking (for testing or accessibility).

    Useful for testing the booking flow without actual audio.
    """
    session_id = input_data.session_id or str(uuid4())

    agent = get_voice_agent()
    response = await agent.process_text(
        text=input_data.text,
        session_id=session_id,
        clinic_id=input_data.clinic_id,
        db=db,
    )

    return _format_response(response, session_id)


@router.get("/session/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: CurrentUser,
):
    """Get the status of a voice booking session."""
    agent = get_voice_agent()
    session = agent.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return {
        "session_id": session_id,
        "state": session.state.value,
        "doctor_name": session.doctor_name,
        "appointment_date": session.appointment_date.isoformat() if session.appointment_date else None,
        "appointment_time": session.appointment_time.isoformat() if session.appointment_time else None,
        "patient_name": session.patient_name,
        "reason": session.reason,
        "conversation_turns": len(session.conversation_history),
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
    }


@router.delete("/session/{session_id}")
async def cancel_session(
    session_id: str,
    current_user: CurrentUser,
):
    """Cancel/end a voice booking session."""
    agent = get_voice_agent()
    session = agent.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    agent._cleanup_session(session_id)

    return {"message": "Session cancelled", "session_id": session_id}


@router.post("/synthesize")
async def synthesize_speech(
    current_user: CurrentUser,
    text: str,
    voice: str = "en_IN",
    speed: float = 1.0,
):
    """
    Synthesize speech from text (TTS only).

    Returns audio as base64 encoded string.
    """
    from app.voice.tts import TextToSpeechAsync

    tts = TextToSpeechAsync(voice)
    audio = await tts.synthesize(text, speed=speed)

    return {
        "text": text,
        "audio_base64": base64.b64encode(audio).decode("utf-8"),
        "voice": voice,
        "format": "wav",
    }


@router.post("/transcribe")
async def transcribe_audio(
    current_user: CurrentUser,
    audio_file: UploadFile = File(...),
    language: Optional[str] = None,
):
    """
    Transcribe audio to text (STT only).

    Returns transcription with confidence score.
    """
    from app.voice.stt import SpeechToTextAsync

    audio_data = await audio_file.read()

    stt = SpeechToTextAsync()
    result = await stt.transcribe(audio_data, language)

    return {
        "text": result["text"],
        "language": result["language"],
        "confidence": result["confidence"],
        "duration": result["duration"],
        "segments": result["segments"],
    }


def _format_response(response: VoiceResponse, session_id: str) -> dict:
    """Format VoiceResponse for API output."""
    return {
        "text": response.text,
        "audio_base64": base64.b64encode(response.audio).decode("utf-8") if response.audio else None,
        "state": response.state.value,
        "booking_complete": response.booking_complete,
        "appointment_id": response.appointment_id,
        "next_action": response.next_action,
        "session_id": session_id,
        "metadata": response.metadata,
    }
