"""
Real-time event service for WebSocket notifications.

This service provides event publishing functions for appointments, waitlist,
and general notifications. It integrates with the WebSocket connection manager
to broadcast events to connected clients.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """WebSocket event types."""

    # Appointment events
    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_UPDATED = "appointment_updated"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_CHECKED_IN = "appointment_checked_in"
    APPOINTMENT_STARTED = "appointment_started"
    APPOINTMENT_COMPLETED = "appointment_completed"
    APPOINTMENT_NO_SHOW = "appointment_no_show"

    # Waitlist events
    WAITLIST_JOINED = "waitlist_joined"
    WAITLIST_UPDATED = "waitlist_updated"
    WAITLIST_SLOT_AVAILABLE = "waitlist_slot_available"
    WAITLIST_BOOKED = "waitlist_booked"
    WAITLIST_EXPIRED = "waitlist_expired"
    WAITLIST_CANCELLED = "waitlist_cancelled"

    # Notification events
    NOTIFICATION_NEW = "notification_new"
    NOTIFICATION_REMINDER = "notification_reminder"
    NOTIFICATION_ALERT = "notification_alert"

    # System events
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_UPDATE = "system_update"


class EventPayload(BaseModel):
    """Base event payload schema."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    clinic_id: UUID
    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class AppointmentEventData(BaseModel):
    """Appointment event data schema."""

    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    token_number: int | None = None
    chief_complaint: str | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class WaitlistEventData(BaseModel):
    """Waitlist event data schema."""

    waitlist_id: UUID
    patient_name: str
    patient_phone: str
    doctor_id: UUID | None = None
    doctor_name: str | None = None
    priority: str
    status: str
    queue_position: int
    preferred_date: str
    offered_slot_time: datetime | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class NotificationEventData(BaseModel):
    """Notification event data schema."""

    notification_id: str
    title: str
    message: str
    priority: str = "normal"  # low, normal, high, urgent
    action_url: str | None = None
    user_id: UUID | None = None


class RealtimeService:
    """
    Real-time event publishing service.

    This service provides methods to publish events to connected WebSocket clients.
    It should be used throughout the application to notify clients of changes.
    """

    def __init__(self):
        """Initialize the realtime service."""
        self._connection_manager = None

    def set_connection_manager(self, manager: Any) -> None:
        """
        Set the WebSocket connection manager.

        Args:
            manager: WebSocket connection manager instance
        """
        self._connection_manager = manager

    async def publish_appointment_event(
        self,
        event_type: EventType,
        clinic_id: UUID,
        appointment_data: AppointmentEventData,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish an appointment-related event.

        Args:
            event_type: Type of appointment event
            clinic_id: Clinic ID for routing
            appointment_data: Appointment event data
            metadata: Additional metadata
        """
        if self._connection_manager is None:
            return

        payload = EventPayload(
            event_type=event_type,
            clinic_id=clinic_id,
            data=appointment_data.model_dump(mode="json"),
            metadata=metadata or {},
        )

        await self._connection_manager.broadcast_to_clinic(
            clinic_id=clinic_id,
            message=payload.model_dump(mode="json"),
        )

    async def publish_waitlist_event(
        self,
        event_type: EventType,
        clinic_id: UUID,
        waitlist_data: WaitlistEventData,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish a waitlist-related event.

        Args:
            event_type: Type of waitlist event
            clinic_id: Clinic ID for routing
            waitlist_data: Waitlist event data
            metadata: Additional metadata
        """
        if self._connection_manager is None:
            return

        payload = EventPayload(
            event_type=event_type,
            clinic_id=clinic_id,
            data=waitlist_data.model_dump(mode="json"),
            metadata=metadata or {},
        )

        await self._connection_manager.broadcast_to_clinic(
            clinic_id=clinic_id,
            message=payload.model_dump(mode="json"),
        )

    async def publish_notification_event(
        self,
        event_type: EventType,
        clinic_id: UUID,
        notification_data: NotificationEventData,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish a notification event.

        Args:
            event_type: Type of notification event
            clinic_id: Clinic ID for routing
            notification_data: Notification event data
            metadata: Additional metadata
        """
        if self._connection_manager is None:
            return

        payload = EventPayload(
            event_type=event_type,
            clinic_id=clinic_id,
            data=notification_data.model_dump(mode="json"),
            metadata=metadata or {},
        )

        await self._connection_manager.broadcast_to_clinic(
            clinic_id=clinic_id,
            message=payload.model_dump(mode="json"),
        )

    async def publish_system_event(
        self,
        event_type: EventType,
        message: str,
        clinic_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish a system-wide event.

        Args:
            event_type: Type of system event
            message: System message
            clinic_id: Optional clinic ID (if None, broadcasts to all)
            metadata: Additional metadata
        """
        if self._connection_manager is None:
            return

        data = {
            "message": message,
            "severity": metadata.get("severity", "info") if metadata else "info",
        }

        if clinic_id:
            payload = EventPayload(
                event_type=event_type,
                clinic_id=clinic_id,
                data=data,
                metadata=metadata or {},
            )
            await self._connection_manager.broadcast_to_clinic(
                clinic_id=clinic_id,
                message=payload.model_dump(mode="json"),
            )
        else:
            # Broadcast to all connected clients
            await self._connection_manager.broadcast_to_all(
                message={
                    "event_type": event_type.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": data,
                    "metadata": metadata or {},
                }
            )


# Singleton instance
_realtime_service: RealtimeService | None = None


def get_realtime_service() -> RealtimeService:
    """
    Get the singleton realtime service instance.

    Returns:
        RealtimeService instance
    """
    global _realtime_service
    if _realtime_service is None:
        _realtime_service = RealtimeService()
    return _realtime_service
