"""
WebSocket endpoints for telemedicine real-time updates.

Provides real-time waiting room status updates to patients.
"""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import WebSocketException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import decode_token
from app.models.consultation import ConsultationStatus
from app.services.telemedicine import TelemedicineService

logger = logging.getLogger(__name__)
router = APIRouter()

# Create async engine for WebSocket connections
engine = create_async_engine(settings.async_database_url, echo=False)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@router.websocket("/ws/waiting-room/{consultation_id}")
async def waiting_room_websocket(
    websocket: WebSocket,
    consultation_id: UUID,
    token: str | None = None,
) -> None:
    """
    WebSocket for real-time waiting room updates.

    Sends periodic status updates to patients waiting for consultation.

    Events sent:
    - queue_position_update: Updated position and wait time
    - doctor_ready: Doctor has admitted patient (includes room URL and JWT)
    - consultation_cancelled: Consultation was cancelled
    - error: Error occurred

    Args:
        websocket: WebSocket connection
        consultation_id: Consultation ID to track
        token: JWT authentication token (query parameter)

    Example client usage:
    ```javascript
    const ws = new WebSocket(
        'ws://localhost:8000/api/v1/ws/waiting-room/123?token=YOUR_JWT'
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === 'doctor_ready') {
            // Patient can now join the consultation
            window.location.href = data.room_url + '?jwt=' + data.jwt_token;
        }
    };
    ```
    """
    # Authenticate
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required",
        )

    try:
        payload = decode_token(token)
        user_id = UUID(payload.get("sub"))
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token",
        )

    await websocket.accept()

    logger.info(
        f"Patient {user_id} connected to waiting room WebSocket for "
        f"consultation {consultation_id}"
    )

    try:
        # Create DB session for this connection
        async with async_session_maker() as db:
            service = TelemedicineService(db)

            # Send initial status
            await websocket.send_json(
                {
                    "event": "connected",
                    "message": "Connected to waiting room",
                    "consultation_id": str(consultation_id),
                }
            )

            # Poll for status updates every 5 seconds
            while True:
                try:
                    # Get current status
                    status_info = await service.get_waiting_room_status(consultation_id)

                    # Check if doctor admitted patient
                    if status_info.status == ConsultationStatus.IN_PROGRESS:
                        # Generate JWT token for patient to join
                        patient_response = await service.patient_join_consultation(
                            consultation_id=consultation_id,
                            user_id=user_id,
                        )

                        await websocket.send_json(
                            {
                                "event": "doctor_ready",
                                "message": "Doctor is ready to see you",
                                "room_url": patient_response.room_url,
                                "jwt_token": patient_response.jwt_token,
                                "room_name": patient_response.room_name,
                            }
                        )

                        logger.info(
                            f"Patient {user_id} admitted to consultation {consultation_id}"
                        )
                        break  # Exit loop, patient can now join

                    # Check if consultation was cancelled
                    elif status_info.status == ConsultationStatus.CANCELLED:
                        await websocket.send_json(
                            {
                                "event": "consultation_cancelled",
                                "message": "This consultation has been cancelled",
                            }
                        )
                        break

                    # Check if patient marked as no-show
                    elif status_info.status == ConsultationStatus.NO_SHOW:
                        await websocket.send_json(
                            {
                                "event": "no_show",
                                "message": "You missed this consultation",
                            }
                        )
                        break

                    # Send queue position update
                    else:
                        await websocket.send_json(
                            {
                                "event": "queue_position_update",
                                "status": status_info.status.value,
                                "position": status_info.position,
                                "estimated_wait_minutes": status_info.estimated_wait_minutes,
                                "patient_joined_at": (
                                    status_info.patient_joined_at.isoformat()
                                    if status_info.patient_joined_at
                                    else None
                                ),
                            }
                        )

                    # Wait before next poll
                    await asyncio.sleep(5)

                except ValueError as e:
                    # Consultation not found or other error
                    await websocket.send_json(
                        {
                            "event": "error",
                            "message": str(e),
                        }
                    )
                    break

    except WebSocketDisconnect:
        logger.info(
            f"Patient {user_id} disconnected from waiting room for "
            f"consultation {consultation_id}"
        )
    except Exception as e:
        logger.error(
            f"Error in waiting room WebSocket for consultation {consultation_id}: {e}",
            exc_info=True,
        )
        try:
            await websocket.send_json(
                {
                    "event": "error",
                    "message": "An error occurred",
                }
            )
        except Exception:
            pass  # Connection might be closed
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/doctor-queue/{doctor_id}")
async def doctor_queue_websocket(
    websocket: WebSocket,
    doctor_id: UUID,
    token: str | None = None,
) -> None:
    """
    WebSocket for doctor's waiting queue updates.

    Sends real-time updates when patients join/leave the waiting room.

    Events sent:
    - patient_joined: New patient in waiting room
    - queue_update: Updated queue list
    - patient_left: Patient left waiting room

    Args:
        websocket: WebSocket connection
        doctor_id: Doctor's user ID
        token: JWT authentication token
    """
    # Authenticate
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required",
        )

    try:
        payload = decode_token(token)
        user_id = UUID(payload.get("sub"))

        # Verify user is the doctor
        if user_id != doctor_id:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Access denied",
            )

    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token",
        )

    await websocket.accept()

    logger.info(
        f"Doctor {doctor_id} connected to queue WebSocket"
    )

    try:
        async with async_session_maker() as db:
            service = TelemedicineService(db)

            await websocket.send_json(
                {
                    "event": "connected",
                    "message": "Connected to doctor queue",
                    "doctor_id": str(doctor_id),
                }
            )

            # Track previous queue to detect changes
            previous_queue_ids = set()

            # Poll for queue updates every 3 seconds
            while True:
                try:
                    # Get current queue
                    queue = await service.get_doctor_queue(doctor_id)

                    current_queue_ids = {item.consultation_id for item in queue}

                    # Detect new patients
                    new_patients = current_queue_ids - previous_queue_ids
                    if new_patients:
                        await websocket.send_json(
                            {
                                "event": "patient_joined",
                                "message": f"{len(new_patients)} new patient(s) in queue",
                                "count": len(new_patients),
                            }
                        )

                    # Detect patients who left
                    left_patients = previous_queue_ids - current_queue_ids
                    if left_patients:
                        await websocket.send_json(
                            {
                                "event": "patient_left",
                                "message": f"{len(left_patients)} patient(s) left queue",
                                "count": len(left_patients),
                            }
                        )

                    # Send queue update
                    await websocket.send_json(
                        {
                            "event": "queue_update",
                            "total_waiting": len(queue),
                            "queue": [
                                {
                                    "consultation_id": str(item.consultation_id),
                                    "patient_id": str(item.patient_id),
                                    "patient_name": item.patient_name,
                                    "wait_time_minutes": item.wait_time_minutes,
                                    "chief_complaint": item.chief_complaint,
                                    "is_emergency": item.is_emergency,
                                }
                                for item in queue
                            ],
                        }
                    )

                    previous_queue_ids = current_queue_ids

                    await asyncio.sleep(3)

                except Exception as e:
                    logger.error(f"Error fetching doctor queue: {e}")
                    await websocket.send_json(
                        {
                            "event": "error",
                            "message": "Error fetching queue",
                        }
                    )
                    await asyncio.sleep(5)  # Longer wait after error

    except WebSocketDisconnect:
        logger.info(f"Doctor {doctor_id} disconnected from queue WebSocket")
    except Exception as e:
        logger.error(
            f"Error in doctor queue WebSocket: {e}",
            exc_info=True,
        )
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
