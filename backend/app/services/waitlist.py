"""
Waitlist Management Service.

Handles patient queues when preferred appointment slots are unavailable:
- Add patients to waitlist with priority
- Auto-notify when slots open
- Process queue by priority
- Estimated wait time calculation
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.waitlist import (
    Waitlist,
    WaitlistPriority,
    WaitlistStatus,
    NotificationChannel,
)
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor

logger = logging.getLogger(__name__)


class WaitlistService:
    """
    Waitlist management service.

    Features:
    - Add to waitlist with priority
    - Process queue when slots open
    - Auto-notify patients
    - Estimate wait times
    - Expire old entries
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def add_to_waitlist(
        self,
        clinic_id: UUID,
        patient_name: str,
        patient_phone: str,
        preferred_date: date,
        doctor_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        alternate_date: Optional[date] = None,
        preferred_time_slot: Optional[str] = None,
        priority: WaitlistPriority = WaitlistPriority.NORMAL,
        chief_complaint: Optional[str] = None,
        is_emergency: bool = False,
        notification_channel: NotificationChannel = NotificationChannel.SMS,
    ) -> Waitlist:
        """
        Add a patient to the waitlist.

        Args:
            clinic_id: Clinic ID
            patient_name: Patient's name
            patient_phone: Patient's phone number
            preferred_date: Preferred appointment date
            doctor_id: Optional specific doctor
            patient_id: Optional existing patient ID
            alternate_date: Alternative date if preferred unavailable
            preferred_time_slot: Preferred time (morning, afternoon, etc.)
            priority: Queue priority level
            chief_complaint: Reason for visit
            is_emergency: Emergency flag
            notification_channel: How to notify patient

        Returns:
            Created waitlist entry
        """
        # Auto-set emergency priority
        if is_emergency:
            priority = WaitlistPriority.EMERGENCY

        # Calculate queue position
        position = await self._get_next_position(clinic_id, doctor_id, preferred_date)

        entry = Waitlist(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            preferred_date=preferred_date,
            alternate_date=alternate_date,
            preferred_time_slot=preferred_time_slot,
            priority=priority.value,
            status=WaitlistStatus.WAITING.value,
            queue_position=position,
            chief_complaint=chief_complaint,
            is_emergency=is_emergency,
            notification_channel=notification_channel.value,
        )

        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(f"Added to waitlist: {patient_name} for {preferred_date}, position {position}")
        return entry

    async def _get_next_position(
        self,
        clinic_id: UUID,
        doctor_id: Optional[UUID],
        preferred_date: date,
    ) -> int:
        """Get next queue position for a date."""
        base_filter = and_(
            Waitlist.clinic_id == clinic_id,
            Waitlist.preferred_date == preferred_date,
            Waitlist.status == WaitlistStatus.WAITING.value,
        )

        if doctor_id:
            base_filter = and_(base_filter, Waitlist.doctor_id == doctor_id)

        result = await self.db.execute(
            select(func.max(Waitlist.queue_position)).where(base_filter)
        )
        max_position = result.scalar() or 0
        return max_position + 1

    async def get_waitlist(
        self,
        clinic_id: UUID,
        doctor_id: Optional[UUID] = None,
        date_filter: Optional[date] = None,
        status: Optional[WaitlistStatus] = None,
        limit: int = 50,
    ) -> list[Waitlist]:
        """
        Get waitlist entries.

        Args:
            clinic_id: Filter by clinic
            doctor_id: Filter by doctor
            date_filter: Filter by date
            status: Filter by status
            limit: Max results

        Returns:
            List of waitlist entries sorted by priority and position
        """
        filters = [Waitlist.clinic_id == clinic_id]

        if doctor_id:
            filters.append(Waitlist.doctor_id == doctor_id)
        if date_filter:
            filters.append(Waitlist.preferred_date == date_filter)
        if status:
            filters.append(Waitlist.status == status.value)
        else:
            # Default to waiting entries
            filters.append(Waitlist.status == WaitlistStatus.WAITING.value)

        result = await self.db.execute(
            select(Waitlist)
            .where(and_(*filters))
            .order_by(
                # Emergency first
                Waitlist.is_emergency.desc(),
                # Then by priority
                Waitlist.priority.asc(),
                # Then by position
                Waitlist.queue_position.asc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_queue_position(self, entry_id: UUID) -> dict:
        """
        Get current position and estimated wait for an entry.

        Returns:
            Dict with position, ahead_count, and estimated_wait_minutes
        """
        entry = await self.db.get(Waitlist, entry_id)
        if not entry:
            return None

        # Count entries ahead
        filters = [
            Waitlist.clinic_id == entry.clinic_id,
            Waitlist.preferred_date == entry.preferred_date,
            Waitlist.status == WaitlistStatus.WAITING.value,
            or_(
                Waitlist.is_emergency > entry.is_emergency,
                and_(
                    Waitlist.is_emergency == entry.is_emergency,
                    Waitlist.priority < entry.priority,
                ),
                and_(
                    Waitlist.is_emergency == entry.is_emergency,
                    Waitlist.priority == entry.priority,
                    Waitlist.queue_position < entry.queue_position,
                ),
            ),
        ]

        if entry.doctor_id:
            filters.append(Waitlist.doctor_id == entry.doctor_id)

        result = await self.db.execute(
            select(func.count()).where(and_(*filters))
        )
        ahead_count = result.scalar() or 0

        # Estimate wait time (rough: 15 min per person)
        estimated_wait = ahead_count * 15

        return {
            "entry_id": str(entry_id),
            "position": entry.queue_position,
            "ahead_count": ahead_count,
            "estimated_wait_minutes": estimated_wait,
            "priority": entry.priority,
            "status": entry.status,
        }

    async def process_cancelled_slot(
        self,
        doctor_id: UUID,
        slot_time: datetime,
        clinic_id: UUID,
    ) -> Optional[Waitlist]:
        """
        Process a cancelled appointment slot.

        Finds the next waitlist patient and notifies them.

        Args:
            doctor_id: Doctor who has the open slot
            slot_time: The available slot time
            clinic_id: Clinic ID

        Returns:
            Waitlist entry that was notified, or None
        """
        slot_date = slot_time.date()

        # Find top candidate
        result = await self.db.execute(
            select(Waitlist)
            .where(
                and_(
                    Waitlist.clinic_id == clinic_id,
                    or_(
                        Waitlist.doctor_id == doctor_id,
                        Waitlist.doctor_id.is_(None),  # Any doctor
                    ),
                    or_(
                        Waitlist.preferred_date == slot_date,
                        Waitlist.alternate_date == slot_date,
                    ),
                    Waitlist.status == WaitlistStatus.WAITING.value,
                )
            )
            .order_by(
                Waitlist.is_emergency.desc(),
                Waitlist.priority.asc(),
                Waitlist.queue_position.asc(),
            )
            .limit(1)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            logger.info(f"No waitlist patients for slot {slot_time}")
            return None

        # Mark as notified
        entry.mark_notified(slot_time, expires_in_minutes=30)
        await self.db.commit()

        # Send notification (would integrate with SMS/WhatsApp)
        await self._send_slot_notification(entry, slot_time)

        logger.info(f"Notified {entry.patient_name} about slot at {slot_time}")
        return entry

    async def _send_slot_notification(
        self,
        entry: Waitlist,
        slot_time: datetime,
    ):
        """
        Send notification about available slot.

        Would integrate with SMS/WhatsApp services.
        """
        # Get doctor name
        doctor_name = "the doctor"
        if entry.doctor_id:
            doctor = await self.db.get(Doctor, entry.doctor_id)
            if doctor:
                doctor_name = f"Dr. {doctor.name}"

        message = (
            f"Hi {entry.patient_name}! Good news - an appointment slot has opened up with "
            f"{doctor_name} on {slot_time.strftime('%B %d at %I:%M %p')}. "
            f"Please confirm within 30 minutes to book this slot. "
            f"Reply YES to confirm or NO to decline."
        )

        # Log for now (would send via SMS/WhatsApp)
        logger.info(f"Sending notification to {entry.patient_phone}: {message}")

        # TODO: Integrate with SMS/WhatsApp service
        # from app.integrations.sms import send_sms
        # await send_sms(entry.patient_phone, message)

    async def confirm_slot(
        self,
        entry_id: UUID,
        appointment_id: UUID,
    ) -> Waitlist:
        """
        Confirm patient took the offered slot.

        Args:
            entry_id: Waitlist entry ID
            appointment_id: Created appointment ID

        Returns:
            Updated waitlist entry
        """
        entry = await self.db.get(Waitlist, entry_id)
        if not entry:
            raise ValueError(f"Waitlist entry {entry_id} not found")

        entry.mark_booked(appointment_id)
        await self.db.commit()

        logger.info(f"Waitlist entry {entry_id} booked as appointment {appointment_id}")
        return entry

    async def decline_slot(self, entry_id: UUID) -> Waitlist:
        """
        Patient declined the offered slot.

        Moves to next in queue and resets this entry.
        """
        entry = await self.db.get(Waitlist, entry_id)
        if not entry:
            raise ValueError(f"Waitlist entry {entry_id} not found")

        # Reset to waiting with lower priority
        entry.status = WaitlistStatus.WAITING.value
        entry.offered_slot_time = None
        entry.slot_offer_expires_at = None
        # Move to end of queue
        entry.queue_position = await self._get_next_position(
            entry.clinic_id,
            entry.doctor_id,
            entry.preferred_date,
        )

        await self.db.commit()
        return entry

    async def cancel_entry(self, entry_id: UUID) -> Waitlist:
        """Cancel a waitlist entry."""
        entry = await self.db.get(Waitlist, entry_id)
        if not entry:
            raise ValueError(f"Waitlist entry {entry_id} not found")

        entry.mark_cancelled()
        await self.db.commit()
        return entry

    async def cleanup_expired(self, clinic_id: UUID) -> int:
        """
        Clean up expired waitlist entries.

        Expires entries where:
        - Preferred date is past
        - Slot offer expired without confirmation

        Returns:
            Number of entries expired
        """
        now = datetime.now(timezone.utc)
        today = date.today()

        # Mark expired
        result = await self.db.execute(
            update(Waitlist)
            .where(
                and_(
                    Waitlist.clinic_id == clinic_id,
                    Waitlist.status.in_([
                        WaitlistStatus.WAITING.value,
                        WaitlistStatus.NOTIFIED.value,
                    ]),
                    or_(
                        # Past preferred date
                        Waitlist.preferred_date < today,
                        # Expired slot offer
                        and_(
                            Waitlist.status == WaitlistStatus.NOTIFIED.value,
                            Waitlist.slot_offer_expires_at < now,
                        ),
                    ),
                )
            )
            .values(status=WaitlistStatus.EXPIRED.value)
        )
        await self.db.commit()

        expired_count = result.rowcount
        if expired_count > 0:
            logger.info(f"Expired {expired_count} waitlist entries")

        return expired_count

    async def get_waitlist_stats(
        self,
        clinic_id: UUID,
        date_filter: Optional[date] = None,
    ) -> dict:
        """
        Get waitlist statistics.

        Returns:
            Dict with counts by status and priority
        """
        filters = [Waitlist.clinic_id == clinic_id]
        if date_filter:
            filters.append(Waitlist.preferred_date == date_filter)

        # Count by status
        status_result = await self.db.execute(
            select(Waitlist.status, func.count())
            .where(and_(*filters))
            .group_by(Waitlist.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # Count by priority (waiting only)
        priority_result = await self.db.execute(
            select(Waitlist.priority, func.count())
            .where(
                and_(
                    *filters,
                    Waitlist.status == WaitlistStatus.WAITING.value,
                )
            )
            .group_by(Waitlist.priority)
        )
        by_priority = {row[0]: row[1] for row in priority_result.all()}

        # Emergency count
        emergency_count = await self.db.execute(
            select(func.count())
            .where(
                and_(
                    *filters,
                    Waitlist.is_emergency == True,
                    Waitlist.status == WaitlistStatus.WAITING.value,
                )
            )
        )

        return {
            "by_status": by_status,
            "by_priority": by_priority,
            "waiting_count": by_status.get(WaitlistStatus.WAITING.value, 0),
            "emergency_count": emergency_count.scalar() or 0,
            "booked_count": by_status.get(WaitlistStatus.BOOKED.value, 0),
        }


def get_waitlist_service(db: AsyncSession) -> WaitlistService:
    """Factory function for waitlist service."""
    return WaitlistService(db)
