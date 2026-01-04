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
    language: str = "en",
    speed: float = 1.0,
    exaggeration: float = 0.5,
):
    """
    Synthesize speech from text using Chatterbox TTS.

    Features:
    - Multi-language support (en, hi, ta, te, bn, mr, gu, kn, ml, pa)
    - Paralinguistic tags in text: [laugh], [cough], [sigh], [gasp], [chuckle]
    - Exaggeration: 0.0 (neutral) to 1.0 (very expressive)

    Returns audio as base64 encoded string.
    """
    from app.voice.tts import TextToSpeechAsync

    tts = TextToSpeechAsync(language)
    audio = await tts.synthesize(
        text,
        language=language,
        speed=speed,
        exaggeration=exaggeration,
    )

    return {
        "text": text,
        "audio_base64": base64.b64encode(audio).decode("utf-8"),
        "language": language,
        "exaggeration": exaggeration,
        "format": "wav",
    }


@router.post("/clone-voice")
async def clone_voice(
    db: DbSession,
    current_user: CurrentUser,
    voice_sample: UploadFile = File(...),
    doctor_id: Optional[UUID] = None,
):
    """
    Upload a voice sample for voice cloning.

    The voice sample should be 3-10 seconds of clear speech.
    Once uploaded, synthesized speech will use this voice.

    Args:
        voice_sample: WAV audio file (3-10 seconds recommended)
        doctor_id: Optional doctor ID to associate voice with
    """
    from pathlib import Path
    from app.voice.tts import ChatterboxTTS

    # Validate file type
    if not voice_sample.filename.endswith(('.wav', '.mp3', '.m4a', '.ogg')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file must be WAV, MP3, M4A, or OGG format",
        )

    # Read audio data
    audio_data = await voice_sample.read()

    # Validate size (limit to 10MB)
    if len(audio_data) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file too large (max 10MB)",
        )

    # Save voice sample
    tts = ChatterboxTTS()
    voice_path = tts.clone_voice_from_bytes(audio_data)

    return {
        "message": "Voice sample uploaded successfully",
        "voice_path": str(voice_path),
        "doctor_id": doctor_id,
        "file_size_bytes": len(audio_data),
    }


@router.post("/synthesize-with-voice")
async def synthesize_with_cloned_voice(
    current_user: CurrentUser,
    text: str,
    voice_sample: UploadFile = File(...),
    language: str = "en",
    exaggeration: float = 0.5,
):
    """
    Synthesize speech using a provided voice sample (zero-shot cloning).

    Upload a voice sample along with text to get speech in that voice.

    Args:
        text: Text to synthesize (can include [laugh], [sigh], etc.)
        voice_sample: Reference voice audio (3-10 seconds)
        language: Language code (en, hi, etc.)
        exaggeration: Emotion intensity 0.0-1.0
    """
    from app.voice.tts import TextToSpeechAsync

    # Read voice sample
    voice_data = await voice_sample.read()

    tts = TextToSpeechAsync(language)
    audio = await tts.synthesize(
        text,
        language=language,
        voice_sample=voice_data,
        exaggeration=exaggeration,
    )

    return {
        "text": text,
        "audio_base64": base64.b64encode(audio).decode("utf-8"),
        "language": language,
        "voice_cloned": True,
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
