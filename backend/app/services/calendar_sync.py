"""
Calendar Sync Service.

Orchestrates synchronization of appointments to Google Calendar.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google_calendar import get_google_calendar_integration
from app.models.appointment import Appointment, AppointmentStatus
from app.models.calendar_settings import DoctorCalendarSettings
from app.models.doctor import Doctor
from app.models.patient import Patient

logger = logging.getLogger(__name__)


class CalendarSyncService:
    """
    Service for syncing appointments to Google Calendar.

    Handles:
    - Appointment event creation
    - Appointment event updates
    - Appointment event deletion
    - Sync status tracking
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize calendar sync service.

        Args:
            db: Async database session
        """
        self.db = db
        self.gcal = get_google_calendar_integration()

    async def get_doctor_calendar_settings(
        self,
        doctor_id: UUID,
    ) -> Optional[DoctorCalendarSettings]:
        """
        Get calendar settings for a doctor.

        Args:
            doctor_id: Doctor UUID

        Returns:
            DoctorCalendarSettings or None if not configured
        """
        result = await self.db.execute(
            select(DoctorCalendarSettings).where(
                DoctorCalendarSettings.doctor_id == doctor_id
            )
        )
        return result.scalar_one_or_none()

    async def sync_appointment(
        self,
        appointment: Appointment,
        force: bool = False,
    ) -> bool:
        """
        Sync an appointment to Google Calendar.

        Creates, updates, or deletes the calendar event based on appointment status.

        Args:
            appointment: Appointment to sync
            force: Force sync even if already synced

        Returns:
            True if sync succeeded, False otherwise
        """
        if not self.gcal.is_configured():
            logger.debug("Google Calendar not configured, skipping sync")
            return False

        # Get calendar settings
        settings = await self.get_doctor_calendar_settings(appointment.doctor_id)
        if not settings or not settings.sync_enabled:
            logger.debug(f"Calendar sync disabled for doctor {appointment.doctor_id}")
            appointment.calendar_sync_status = "skipped"
            return False

        try:
            # Load relationships if not already loaded
            if not appointment.patient:
                await self.db.refresh(appointment, ["patient"])
            if not appointment.doctor:
                await self.db.refresh(appointment, ["doctor"])

            # Handle different appointment states
            if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
                return await self._delete_calendar_event(appointment, settings)
            else:
                # Check if event exists
                if appointment.google_calendar_event_id and not force:
                    return await self._update_calendar_event(appointment, settings)
                else:
                    return await self._create_calendar_event(appointment, settings)

        except Exception as e:
            logger.error(f"Error syncing appointment {appointment.id}: {e}")
            appointment.calendar_sync_status = "failed"
            appointment.calendar_sync_error = str(e)
            appointment.last_calendar_sync_at = datetime.now(timezone.utc)
            settings.total_failed += 1
            settings.last_sync_error = str(e)
            await self.db.commit()
            return False

    async def _create_calendar_event(
        self,
        appointment: Appointment,
        settings: DoctorCalendarSettings,
    ) -> bool:
        """Create a new calendar event for appointment."""
        try:
            # Build event details
            summary = f"Appointment: {appointment.patient.first_name} {appointment.patient.last_name or ''}"
            description = self._build_event_description(appointment)
            location = appointment.doctor.clinic.address if appointment.doctor.clinic else None

            # Create event
            event_id = self.gcal.create_event(
                refresh_token=settings.google_refresh_token,
                calendar_id=settings.google_calendar_id,
                summary=summary,
                description=description,
                start_time=appointment.scheduled_start,
                end_time=appointment.scheduled_end,
                location=location,
                visibility=settings.event_visibility,
                reminders=settings.event_reminders,
            )

            # Update appointment
            appointment.google_calendar_event_id = event_id
            appointment.calendar_sync_status = "synced"
            appointment.calendar_sync_error = None
            appointment.last_calendar_sync_at = datetime.now(timezone.utc)

            # Update settings stats
            settings.total_synced += 1
            settings.last_synced_at = datetime.now(timezone.utc)
            settings.last_sync_error = None

            await self.db.commit()

            logger.info(f"Created calendar event for appointment {appointment.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            raise

    async def _update_calendar_event(
        self,
        appointment: Appointment,
        settings: DoctorCalendarSettings,
    ) -> bool:
        """Update an existing calendar event."""
        if not appointment.google_calendar_event_id:
            logger.warning(f"No calendar event ID for appointment {appointment.id}, creating new")
            return await self._create_calendar_event(appointment, settings)

        try:
            # Build event details
            summary = f"Appointment: {appointment.patient.first_name} {appointment.patient.last_name or ''}"
            description = self._build_event_description(appointment)
            location = appointment.doctor.clinic.address if appointment.doctor.clinic else None

            # Update event
            self.gcal.update_event(
                refresh_token=settings.google_refresh_token,
                calendar_id=settings.google_calendar_id,
                event_id=appointment.google_calendar_event_id,
                summary=summary,
                description=description,
                start_time=appointment.scheduled_start,
                end_time=appointment.scheduled_end,
                location=location,
                visibility=settings.event_visibility,
            )

            # Update appointment
            appointment.calendar_sync_status = "synced"
            appointment.calendar_sync_error = None
            appointment.last_calendar_sync_at = datetime.now(timezone.utc)

            # Update settings stats
            settings.total_synced += 1
            settings.last_synced_at = datetime.now(timezone.utc)
            settings.last_sync_error = None

            await self.db.commit()

            logger.info(f"Updated calendar event for appointment {appointment.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            raise

    async def _delete_calendar_event(
        self,
        appointment: Appointment,
        settings: DoctorCalendarSettings,
    ) -> bool:
        """Delete a calendar event."""
        if not appointment.google_calendar_event_id:
            logger.debug(f"No calendar event to delete for appointment {appointment.id}")
            appointment.calendar_sync_status = "skipped"
            return True

        try:
            # Delete event
            self.gcal.delete_event(
                refresh_token=settings.google_refresh_token,
                calendar_id=settings.google_calendar_id,
                event_id=appointment.google_calendar_event_id,
            )

            # Update appointment
            appointment.google_calendar_event_id = None
            appointment.calendar_sync_status = "deleted"
            appointment.calendar_sync_error = None
            appointment.last_calendar_sync_at = datetime.now(timezone.utc)

            # Update settings stats
            settings.last_synced_at = datetime.now(timezone.utc)
            settings.last_sync_error = None

            await self.db.commit()

            logger.info(f"Deleted calendar event for appointment {appointment.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            raise

    def _build_event_description(self, appointment: Appointment) -> str:
        """
        Build event description with appointment details.

        Args:
            appointment: Appointment object

        Returns:
            Formatted event description
        """
        lines = [
            f"Patient: {appointment.patient.first_name} {appointment.patient.last_name or ''}",
            f"Phone: {appointment.patient.phone}",
            f"Type: {appointment.appointment_type.replace('_', ' ').title()}",
        ]

        if appointment.chief_complaint:
            lines.append(f"Reason: {appointment.chief_complaint}")

        if appointment.notes:
            lines.append(f"Notes: {appointment.notes}")

        lines.extend([
            "",
            "---",
            "Booked via DocAssist Practice Manager",
        ])

        return "\n".join(lines)

    async def check_conflicts(
        self,
        doctor_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict]:
        """
        Check for calendar conflicts at a specific time.

        Args:
            doctor_id: Doctor UUID
            start_time: Start time to check
            end_time: End time to check

        Returns:
            List of conflicting events
        """
        if not self.gcal.is_configured():
            return []

        settings = await self.get_doctor_calendar_settings(doctor_id)
        if not settings or not settings.sync_enabled:
            return []

        try:
            conflicts = self.gcal.check_conflicts(
                refresh_token=settings.google_refresh_token,
                calendar_id=settings.google_calendar_id,
                start_time=start_time,
                end_time=end_time,
            )
            return conflicts
        except Exception as e:
            logger.error(f"Error checking conflicts: {e}")
            return []

    async def sync_multiple_appointments(
        self,
        doctor_id: UUID,
        since: Optional[datetime] = None,
    ) -> dict:
        """
        Sync multiple appointments for a doctor.

        Args:
            doctor_id: Doctor UUID
            since: Only sync appointments modified since this time

        Returns:
            Dict with sync statistics
        """
        settings = await self.get_doctor_calendar_settings(doctor_id)
        if not settings or not settings.sync_enabled:
            return {"error": "Calendar sync not enabled", "synced": 0, "failed": 0}

        # Build query
        query = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_start >= datetime.now(timezone.utc),  # Only future appointments
        )

        if since:
            query = query.where(Appointment.updated_at >= since)

        # Get appointments
        result = await self.db.execute(query)
        appointments = result.scalars().all()

        # Sync each appointment
        stats = {"synced": 0, "failed": 0, "errors": []}

        for appointment in appointments:
            try:
                success = await self.sync_appointment(appointment)
                if success:
                    stats["synced"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"Appointment {appointment.id}: {str(e)}")

        return stats

    async def disconnect_calendar(self, doctor_id: UUID) -> bool:
        """
        Disconnect Google Calendar and optionally delete all synced events.

        Args:
            doctor_id: Doctor UUID

        Returns:
            True if successful
        """
        settings = await self.get_doctor_calendar_settings(doctor_id)
        if not settings:
            return True

        try:
            # Get all appointments with calendar events
            result = await self.db.execute(
                select(Appointment).where(
                    Appointment.doctor_id == doctor_id,
                    Appointment.google_calendar_event_id.isnot(None),
                )
            )
            appointments = result.scalars().all()

            # Delete all calendar events
            for appointment in appointments:
                try:
                    self.gcal.delete_event(
                        refresh_token=settings.google_refresh_token,
                        calendar_id=settings.google_calendar_id,
                        event_id=appointment.google_calendar_event_id,
                    )
                    appointment.google_calendar_event_id = None
                    appointment.calendar_sync_status = "disconnected"
                except Exception as e:
                    logger.warning(f"Failed to delete event {appointment.google_calendar_event_id}: {e}")

            # Delete settings
            await self.db.delete(settings)
            await self.db.commit()

            logger.info(f"Disconnected calendar for doctor {doctor_id}")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting calendar: {e}")
            return False
