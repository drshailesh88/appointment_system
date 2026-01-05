"""
Daily Digest Service.

Phase 16c: Practice AI - Proactive Intelligence

Generates personalized daily digests for users.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.insight import InsightType, UserDigestPreferences
from app.models.payment import Payment
from app.models.waitlist import Waitlist
from app.schemas.insights import DailyDigest
from app.services.proactive_insights import ProactiveInsightsEngine

logger = logging.getLogger(__name__)


class DailyDigestService:
    """
    Generate and deliver daily digests.

    Features:
    - Personalized morning digest
    - Key metrics and insights
    - Scheduled delivery via push/email
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.insights_engine = ProactiveInsightsEngine(db)

    async def generate_digest(
        self,
        clinic_id: UUID,
        user_id: UUID,
        target_date: Optional[date] = None,
    ) -> DailyDigest:
        """
        Generate daily digest for a user.

        Args:
            clinic_id: Clinic ID
            user_id: User ID
            target_date: Target date (default: today)

        Returns:
            Daily digest
        """
        if target_date is None:
            target_date = date.today()

        yesterday = target_date - timedelta(days=1)

        # Get user preferences
        prefs = await self.get_user_preferences(user_id)

        # Get appointments for today
        appointments_today = await self._get_appointments_count(clinic_id, target_date)

        # Get revenue for yesterday
        revenue_yesterday = await self._get_revenue(clinic_id, yesterday)

        # Get insights
        all_insights = await self.insights_engine.generate_daily_insights(
            clinic_id=clinic_id,
            target_date=target_date,
        )

        # Filter insights based on user preferences
        pending_followups = []
        schedule_alerts = []
        waitlist_opportunities = []
        key_insights = []

        for insight in all_insights:
            if prefs and not prefs.enabled:
                continue

            insight_type = insight.insight_type

            if insight_type == InsightType.FOLLOWUP_DUE.value:
                if not prefs or prefs.include_followups:
                    pending_followups.append(insight)

            elif insight_type == InsightType.SCHEDULE_GAP.value:
                if not prefs or prefs.include_schedule_gaps:
                    schedule_alerts.append(insight)

            elif insight_type == InsightType.WAITLIST_OPPORTUNITY.value:
                if not prefs or prefs.include_waitlist:
                    waitlist_opportunities.append(insight)

            else:
                key_insights.append(insight)

        return DailyDigest(
            date=datetime.combine(target_date, datetime.min.time()),
            appointments_today=appointments_today,
            revenue_yesterday=revenue_yesterday,
            pending_followups=pending_followups[:5],  # Top 5
            schedule_alerts=schedule_alerts[:3],  # Top 3
            waitlist_opportunities=waitlist_opportunities[:3],  # Top 3
            key_insights=key_insights[:5],  # Top 5
        )

    async def get_user_preferences(
        self,
        user_id: UUID,
    ) -> Optional[UserDigestPreferences]:
        """
        Get user's digest preferences.

        Args:
            user_id: User ID

        Returns:
            Preferences or None
        """
        stmt = select(UserDigestPreferences).where(
            UserDigestPreferences.user_id == user_id
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_preferences(
        self,
        user_id: UUID,
        clinic_id: UUID,
        **kwargs,
    ) -> UserDigestPreferences:
        """
        Create or update user preferences.

        Args:
            user_id: User ID
            clinic_id: Clinic ID
            **kwargs: Preference fields

        Returns:
            Updated preferences
        """
        # Check if exists
        prefs = await self.get_user_preferences(user_id)

        if prefs:
            # Update
            for key, value in kwargs.items():
                if hasattr(prefs, key) and value is not None:
                    setattr(prefs, key, value)
        else:
            # Create
            prefs = UserDigestPreferences(
                user_id=user_id,
                clinic_id=clinic_id,
                **kwargs,
            )
            self.db.add(prefs)

        await self.db.commit()
        await self.db.refresh(prefs)

        return prefs

    async def schedule_digest(
        self,
        clinic_id: UUID,
        user_id: UUID,
        delivery_hour: int = 8,
        delivery_minute: int = 0,
    ) -> UserDigestPreferences:
        """
        Schedule daily digest delivery.

        Args:
            clinic_id: Clinic ID
            user_id: User ID
            delivery_hour: Hour (0-23)
            delivery_minute: Minute (0-59)

        Returns:
            Updated preferences
        """
        return await self.create_or_update_preferences(
            user_id=user_id,
            clinic_id=clinic_id,
            enabled=True,
            delivery_hour=delivery_hour,
            delivery_minute=delivery_minute,
        )

    async def send_digest(
        self,
        clinic_id: UUID,
        user_id: UUID,
    ):
        """
        Send digest to user via configured channels.

        Args:
            clinic_id: Clinic ID
            user_id: User ID
        """
        # Get preferences
        prefs = await self.get_user_preferences(user_id)

        if not prefs or not prefs.enabled:
            logger.info(f"Digest disabled for user {user_id}")
            return

        # Generate digest
        digest = await self.generate_digest(clinic_id, user_id)

        # Format digest message
        message = self._format_digest_message(digest)

        # Send via configured channels
        for channel in prefs.channels:
            if channel == "push":
                await self._send_push_notification(user_id, message)
            elif channel == "email":
                await self._send_email(user_id, message, digest)
            elif channel == "sms":
                await self._send_sms(user_id, message)

        logger.info(f"Sent digest to user {user_id} via {prefs.channels}")

    def _format_digest_message(self, digest: DailyDigest) -> str:
        """Format digest as text message."""
        lines = [
            "🌅 Good Morning! Here's your practice summary:",
            "",
            f"📅 Appointments Today: {digest.appointments_today}",
            f"💰 Revenue Yesterday: ₹{digest.revenue_yesterday:,.0f}",
            "",
        ]

        if digest.pending_followups:
            lines.append(f"⚕️ {len(digest.pending_followups)} Follow-ups Due")

        if digest.schedule_alerts:
            lines.append(f"⏰ {len(digest.schedule_alerts)} Schedule Alerts")

        if digest.key_insights:
            lines.append("")
            lines.append("💡 Key Insights:")
            for insight in digest.key_insights[:3]:
                lines.append(f"  • {insight.title}")

        return "\n".join(lines)

    async def _send_push_notification(self, user_id: UUID, message: str):
        """Send push notification (placeholder)."""
        # TODO: Integrate with push_notifications service
        logger.info(f"Would send push to {user_id}: {message[:50]}...")

    async def _send_email(self, user_id: UUID, message: str, digest: DailyDigest):
        """Send email (placeholder)."""
        # TODO: Integrate with email service
        logger.info(f"Would send email to {user_id}")

    async def _send_sms(self, user_id: UUID, message: str):
        """Send SMS (placeholder)."""
        # TODO: Integrate with SMS service (MSG91)
        logger.info(f"Would send SMS to {user_id}")

    async def _get_appointments_count(
        self,
        clinic_id: UUID,
        target_date: date,
    ) -> int:
        """Get appointment count for a date."""
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        stmt = select(func.count(Appointment.id)).where(
            and_(
                Appointment.clinic_id == clinic_id,
                Appointment.appointment_date >= start_datetime,
                Appointment.appointment_date <= end_datetime,
                Appointment.status.in_(["scheduled", "confirmed"]),
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _get_revenue(
        self,
        clinic_id: UUID,
        target_date: date,
    ) -> float:
        """Get revenue for a date."""
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        stmt = select(func.sum(Payment.amount)).where(
            and_(
                Payment.clinic_id == clinic_id,
                Payment.payment_date >= start_datetime,
                Payment.payment_date <= end_datetime,
                Payment.status == "completed",
            )
        )

        result = await self.db.execute(stmt)
        return float(result.scalar() or 0)

    async def _get_waitlist_count(
        self,
        clinic_id: UUID,
    ) -> int:
        """Get active waitlist count."""
        stmt = select(func.count(Waitlist.id)).where(
            and_(
                Waitlist.clinic_id == clinic_id,
                Waitlist.status == "waiting",
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar() or 0
