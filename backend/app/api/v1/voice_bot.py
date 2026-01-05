"""
Voice Bot API endpoints for Twilio webhooks and management.

Phase 18: Voice Bot / Phone Automation
"""

import base64
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy import func

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models.phone_call import CallStatus, CallTranscriptSegment, PhoneCall
from app.schemas.voice_bot import (
    CallStatsResponse,
    OutboundCallRequest,
    OutboundCallResponse,
    PhoneCallResponse,
    PhoneCallWithTranscript,
    TranscriptSegmentResponse,
)
from app.services.voice_bot import AppointmentBookingBot, TelephonyService

logger = logging.getLogger(__name__)

router = APIRouter()


# Telephony service singleton
_telephony_service: Optional[TelephonyService] = None


def get_telephony_service() -> TelephonyService:
    """Get or create telephony service singleton."""
    global _telephony_service
    if _telephony_service is None:
        _telephony_service = TelephonyService(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            phone_number=settings.twilio_phone_number,
            webhook_url=settings.twilio_webhook_url,
        )
    return _telephony_service


# Active voice bot sessions (in-memory cache)
# In production, use Redis for distributed sessions
_active_sessions: dict[str, AppointmentBookingBot] = {}


@router.post("/incoming", response_class=PlainTextResponse)
async def handle_incoming_call(
    request: Request,
    db: DbSession,
):
    """
    Twilio webhook for incoming calls.
    Returns TwiML to connect to WebSocket.
    """
    try:
        from app.core.security import verify_twilio_signature

        # Verify Twilio signature if auth token is configured
        if settings.twilio_auth_token:
            signature = request.headers.get("X-Twilio-Signature", "")
            if not signature:
                logger.warning("Twilio webhook missing signature header")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Twilio signature",
                )

            # Get full URL including protocol and domain
            url = str(request.url)

            # Get form params as dict
            form_data = await request.form()
            params = {key: value for key, value in form_data.items()}

            if not verify_twilio_signature(
                url,
                params,
                signature,
                settings.twilio_auth_token,
            ):
                logger.warning("Twilio webhook signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Twilio signature",
                )
        else:
            form_data = await request.form()
            params = {key: value for key, value in form_data.items()}

        call_sid = params.get("CallSid")
        from_number = params.get("From")
        to_number = params.get("To")

        logger.info(f"Incoming call: {call_sid} from {from_number} to {to_number}")

        # Determine clinic ID from phone number
        clinic_id = await _get_clinic_for_phone_number(db, to_number)
        if not clinic_id:
            logger.error(f"No clinic found for phone number: {to_number}")
            # Return TwiML to say "Number not configured"
            return PlainTextResponse(
                '<?xml version="1.0" encoding="UTF-8"?><Response><Say>This number is not configured.</Say></Response>',
                media_type="application/xml",
            )

        # Create phone call record
        call = PhoneCall(
            id=uuid4(),
            call_sid=call_sid,
            from_number=from_number,
            to_number=to_number,
            direction="inbound",
            status=CallStatus.RINGING,
            clinic_id=clinic_id,
            started_at=datetime.utcnow(),
        )
        db.add(call)
        db.commit()

        logger.info(f"Phone call record created: {call.id}")

        # Return TwiML to connect WebSocket
        telephony = get_telephony_service()
        twiml = telephony.generate_twiml_connect(call_sid)

        return PlainTextResponse(twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling incoming call: {e}", exc_info=True)
        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response><Say>An error occurred.</Say></Response>',
            media_type="application/xml",
        )


@router.websocket("/ws/{call_sid}")
async def voice_bot_websocket(
    websocket: WebSocket,
    call_sid: str,
    db: DbSession,
):
    """
    WebSocket endpoint for real-time audio streaming.

    Receives audio from Twilio, processes with STT,
    generates response with LLM, converts to speech with TTS,
    sends audio back to Twilio.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: {call_sid}")

    try:
        # Get call record
        call = db.query(PhoneCall).filter(PhoneCall.call_sid == call_sid).first()
        if not call:
            logger.error(f"Call not found: {call_sid}")
            await websocket.close()
            return

        # Update call status
        call.status = CallStatus.IN_PROGRESS
        call.answered_at = datetime.utcnow()
        db.commit()

        # Initialize voice bot
        bot = AppointmentBookingBot(db, call.clinic_id)
        _active_sessions[call_sid] = bot

        # Send greeting
        greeting = await bot.handle_call_start(call_sid, call.from_number, call.id)
        logger.info(f"Bot greeting: {greeting}")

        # Convert greeting to audio
        greeting_audio = await bot.tts.synthesize(greeting, language=bot.state.language)

        # Send greeting audio to Twilio
        # Twilio Media Stream expects base64-encoded mulaw audio
        greeting_audio_base64 = base64.b64encode(greeting_audio).decode("utf-8")
        await websocket.send_json({
            "event": "media",
            "streamSid": call_sid,
            "media": {
                "payload": greeting_audio_base64,
            },
        })

        # Save greeting to transcript
        _save_transcript_segment(
            db,
            call.id,
            speaker="bot",
            text=greeting,
            start_time_ms=0,
            end_time_ms=len(greeting_audio),
        )

        # Audio buffer for accumulating chunks
        audio_buffer = []
        stream_start_time = datetime.utcnow()

        while True:
            # Receive message from Twilio
            message = await websocket.receive_json()

            event = message.get("event")

            if event == "connected":
                logger.info(f"Twilio stream connected: {call_sid}")

            elif event == "start":
                logger.info(f"Twilio stream started: {call_sid}")
                stream_start_time = datetime.utcnow()

            elif event == "media":
                # Receive audio chunk
                media = message.get("media", {})
                payload = media.get("payload")

                if payload:
                    # Decode audio (mulaw base64)
                    audio_chunk = base64.b64decode(payload)
                    audio_buffer.append(audio_chunk)

                    # Process audio when buffer reaches threshold (e.g., 1 second)
                    if len(audio_buffer) >= 50:  # Adjust threshold as needed
                        # Combine audio chunks
                        combined_audio = b"".join(audio_buffer)
                        audio_buffer = []

                        # STT
                        try:
                            result = await bot.stt.transcribe(combined_audio)
                            text = result.get("text", "").strip()

                            if text:
                                logger.info(f"Transcribed: {text}")

                                # Save caller transcript
                                _save_transcript_segment(
                                    db,
                                    call.id,
                                    speaker="caller",
                                    text=text,
                                    start_time_ms=int((datetime.utcnow() - stream_start_time).total_seconds() * 1000),
                                    end_time_ms=int((datetime.utcnow() - stream_start_time).total_seconds() * 1000),
                                    language=result.get("language"),
                                    confidence=result.get("confidence"),
                                )

                                # Process with bot
                                response = await bot.process_speech(text)
                                logger.info(f"Bot response: {response}")

                                # Save bot transcript
                                _save_transcript_segment(
                                    db,
                                    call.id,
                                    speaker="bot",
                                    text=response,
                                    start_time_ms=int((datetime.utcnow() - stream_start_time).total_seconds() * 1000),
                                    end_time_ms=int((datetime.utcnow() - stream_start_time).total_seconds() * 1000),
                                )

                                # TTS
                                audio = await bot.tts.synthesize(response, language=bot.state.language)

                                # Send back to Twilio
                                audio_base64 = base64.b64encode(audio).decode("utf-8")
                                await websocket.send_json({
                                    "event": "media",
                                    "streamSid": call_sid,
                                    "media": {
                                        "payload": audio_base64,
                                    },
                                })

                        except Exception as e:
                            logger.error(f"Error processing audio: {e}", exc_info=True)

            elif event == "stop":
                logger.info(f"Twilio stream stopped: {call_sid}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {call_sid}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        # Cleanup
        if call_sid in _active_sessions:
            bot = _active_sessions[call_sid]

            # Update call record
            call = db.query(PhoneCall).filter(PhoneCall.call_sid == call_sid).first()
            if call:
                call.status = CallStatus.COMPLETED
                call.ended_at = datetime.utcnow()
                call.duration_seconds = int((call.ended_at - call.answered_at).total_seconds()) if call.answered_at else 0
                call.transcript = bot.get_full_transcript()
                call.intent_detected = bot.state.intent
                call.language_detected = bot.state.language
                call.patient_id = bot.state.patient_id
                db.commit()

            del _active_sessions[call_sid]

        logger.info(f"WebSocket cleanup complete: {call_sid}")


@router.post("/status")
async def call_status_callback(
    request: Request,
    db: DbSession,
):
    """Twilio status callback."""
    try:
        from app.core.security import verify_twilio_signature

        # Verify Twilio signature if auth token is configured
        if settings.twilio_auth_token:
            signature = request.headers.get("X-Twilio-Signature", "")
            if not signature:
                logger.warning("Twilio status webhook missing signature header")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Twilio signature",
                )

            url = str(request.url)
            form_data = await request.form()
            params = {key: value for key, value in form_data.items()}

            if not verify_twilio_signature(
                url,
                params,
                signature,
                settings.twilio_auth_token,
            ):
                logger.warning("Twilio status webhook signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Twilio signature",
                )
        else:
            form_data = await request.form()
            params = {key: value for key, value in form_data.items()}

        call_sid = params.get("CallSid")
        call_status = params.get("CallStatus")
        duration = params.get("CallDuration")

        logger.info(f"Call status: {call_sid} - {call_status}")

        # Update call record
        call = db.query(PhoneCall).filter(PhoneCall.call_sid == call_sid).first()
        if call:
            call.status = call_status
            if duration:
                call.duration_seconds = int(duration)
            db.commit()

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error in status callback: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/outbound", response_model=OutboundCallResponse)
async def initiate_outbound_call(
    request: OutboundCallRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Initiate outbound call (e.g., appointment reminder)."""
    try:
        telephony = get_telephony_service()

        # Initiate call
        result = await telephony.initiate_outbound_call(
            to_number=request.to_number,
            clinic_id=request.clinic_id,
            purpose=request.purpose,
            appointment_id=request.appointment_id,
        )

        # Create call record
        call = PhoneCall(
            id=uuid4(),
            call_sid=result["call_sid"],
            from_number=result["from_number"],
            to_number=result["to_number"],
            direction="outbound",
            status=result["status"],
            clinic_id=request.clinic_id,
            appointment_id=request.appointment_id,
            patient_id=request.patient_id,
            started_at=datetime.utcnow(),
            metadata=request.metadata,
        )
        db.add(call)
        db.commit()

        return OutboundCallResponse(
            call_sid=result["call_sid"],
            status=result["status"],
            call_id=call.id,
        )

    except Exception as e:
        logger.error(f"Error initiating outbound call: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}",
        )


@router.get("/calls", response_model=list[PhoneCallResponse])
async def list_calls(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List phone calls for a clinic."""
    try:
        query = db.query(PhoneCall)

        if clinic_id:
            query = query.filter(PhoneCall.clinic_id == clinic_id)

        calls = query.order_by(PhoneCall.created_at.desc()).limit(limit).offset(offset).all()

        return calls

    except Exception as e:
        logger.error(f"Error listing calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/calls/{call_id}", response_model=PhoneCallWithTranscript)
async def get_call_details(
    call_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get call details including transcript."""
    try:
        call = db.query(PhoneCall).filter(PhoneCall.id == call_id).first()

        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Call not found",
            )

        return call

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting call details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/calls/{call_id}/transcript", response_model=list[TranscriptSegmentResponse])
async def get_call_transcript(
    call_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get full call transcript."""
    try:
        segments = (
            db.query(CallTranscriptSegment)
            .filter(CallTranscriptSegment.call_id == call_id)
            .order_by(CallTranscriptSegment.start_time_ms)
            .all()
        )

        return segments

    except Exception as e:
        logger.error(f"Error getting transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/stats", response_model=CallStatsResponse)
async def get_call_stats(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: Optional[UUID] = None,
):
    """Get call statistics."""
    try:
        query = db.query(PhoneCall)

        if clinic_id:
            query = query.filter(PhoneCall.clinic_id == clinic_id)

        total_calls = query.count()
        inbound_calls = query.filter(PhoneCall.direction == "inbound").count()
        outbound_calls = query.filter(PhoneCall.direction == "outbound").count()
        completed_calls = query.filter(PhoneCall.status == CallStatus.COMPLETED).count()
        failed_calls = query.filter(PhoneCall.status.in_([CallStatus.FAILED, CallStatus.NO_ANSWER])).count()

        avg_duration = query.filter(
            PhoneCall.duration_seconds.isnot(None)
        ).with_entities(
            func.avg(PhoneCall.duration_seconds)
        ).scalar() or 0.0

        # Appointments stats
        appointments_booked = query.filter(
            PhoneCall.intent_detected == "book_appointment",
            PhoneCall.appointment_id.isnot(None),
        ).count()

        appointments_rescheduled = query.filter(
            PhoneCall.intent_detected == "reschedule_appointment"
        ).count()

        appointments_cancelled = query.filter(
            PhoneCall.intent_detected == "cancel_appointment"
        ).count()

        # Language distribution
        languages = {}
        lang_results = (
            query.filter(PhoneCall.language_detected.isnot(None))
            .with_entities(PhoneCall.language_detected, func.count(PhoneCall.id))
            .group_by(PhoneCall.language_detected)
            .all()
        )
        for lang, count in lang_results:
            languages[lang] = count

        # Intent distribution
        intents = {}
        intent_results = (
            query.filter(PhoneCall.intent_detected.isnot(None))
            .with_entities(PhoneCall.intent_detected, func.count(PhoneCall.id))
            .group_by(PhoneCall.intent_detected)
            .all()
        )
        for intent, count in intent_results:
            intents[intent] = count

        return CallStatsResponse(
            total_calls=total_calls,
            inbound_calls=inbound_calls,
            outbound_calls=outbound_calls,
            completed_calls=completed_calls,
            failed_calls=failed_calls,
            average_duration_seconds=float(avg_duration),
            appointments_booked=appointments_booked,
            appointments_rescheduled=appointments_rescheduled,
            appointments_cancelled=appointments_cancelled,
            languages=languages,
            intents=intents,
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Helper functions

async def _get_clinic_for_phone_number(db: DbSession, phone_number: str) -> Optional[UUID]:
    """Get clinic ID for a phone number."""
    # TODO: Implement phone number -> clinic mapping
    # For now, return first clinic
    from app.models.clinic import Clinic

    clinic = db.query(Clinic).first()
    return clinic.id if clinic else None


def _save_transcript_segment(
    db: DbSession,
    call_id: UUID,
    speaker: str,
    text: str,
    start_time_ms: int,
    end_time_ms: int,
    language: Optional[str] = None,
    confidence: Optional[float] = None,
    entities: Optional[dict] = None,
):
    """Save transcript segment to database."""
    try:
        segment = CallTranscriptSegment(
            id=uuid4(),
            call_id=call_id,
            speaker=speaker,
            text=text,
            language=language,
            confidence=confidence,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            entities=entities or {},
        )
        db.add(segment)
        db.commit()

    except Exception as e:
        logger.error(f"Error saving transcript segment: {e}", exc_info=True)
        db.rollback()
