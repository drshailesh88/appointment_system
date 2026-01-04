"""
Proactive Insights Engine.

Phase 16c: Practice AI - Proactive Intelligence

Generates smart notifications and suggestions based on practice patterns.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.insight import InsightPriority, InsightType, ProactiveInsight
from app.models.payment import Payment
from app.models.procedure import Procedure
from app.schemas.insights import ProactiveInsightCreate, ProactiveInsightResponse
from app.services.followup_intelligence import FollowupIntelligence
from app.services.schedule_optimizer import ScheduleOptimizer

logger = logging.getLogger(__name__)


class ProactiveInsightsEngine:
    """
    Generate proactive insights for the practice.

    Features:
    - Follow-up reminders
    - Schedule gap opportunities
    - Revenue anomalies
    - No-show risk detection
    - Waitlist opportunities
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.followup_intelligence = FollowupIntelligence(db)
        self.schedule_optimizer = ScheduleOptimizer(db)

    async def generate_daily_insights(
        self,
        clinic_id: UUID,
        target_date: Optional[date] = None,
    ) -> list[ProactiveInsightResponse]:
        """
        Generate daily insights for a clinic.

        Args:
            clinic_id: Clinic ID
            target_date: Target date (default: today)

        Returns:
            List of insights
        """
        if target_date is None:
            target_date = date.today()

        insights = []

        # Get follow-up reminders
        followup_insights = await self.get_followup_reminders(clinic_id)
        insights.extend(followup_insights)

        # Get schedule gaps
        gap_insights = await self.find_schedule_gaps(clinic_id, target_date)
        insights.extend(gap_insights)

        # Get revenue anomalies
        revenue_insights = await self.detect_revenue_anomalies(clinic_id)
        insights.extend(revenue_insights)

        # Get no-show risks
        noshow_insights = await self.identify_no_show_risks(clinic_id, target_date)
        insights.extend(noshow_insights)

        logger.info(f"Generated {len(insights)} insights for clinic {clinic_id}")

        return insights

    async def get_followup_reminders(
        self,
        clinic_id: UUID,
        doctor_id: Optional[UUID] = None,
    ) -> list[ProactiveInsightResponse]:
        """
        Get follow-up reminder insights.

        Args:
            clinic_id: Clinic ID
            doctor_id: Optional doctor filter

        Returns:
            List of follow-up insights
        """
        # Get pending follow-ups
        reminders = await self.followup_intelligence.get_pending_followups(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            days_ahead=7,
        )

        # Get overdue follow-ups
        overdue = await self.followup_intelligence.get_overdue_followups(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
        )

        insights = []

        # Create insights for overdue (high priority)
        for reminder in overdue[:5]:  # Limit to top 5
            insight = ProactiveInsight(
                clinic_id=clinic_id,
                patient_id=reminder.patient_id,
                doctor_id=None,  # Would set from reminder
                insight_type=InsightType.FOLLOWUP_DUE.value,
                priority=InsightPriority.URGENT.value,
                title=f"Overdue: {reminder.patient_name} - {reminder.reason}",
                message=f"{reminder.patient_name} is {reminder.days_overdue} days overdue for {reminder.reason} after {reminder.procedure_type}",
                suggested_action={
                    "action": "book_appointment",
                    "patient_id": str(reminder.patient_id),
                    "reason": reminder.reason,
                },
                expires_at=datetime.now() + timedelta(days=7),
            )
            self.db.add(insight)
            insights.append(insight)

        # Create insights for upcoming (medium priority)
        for reminder in reminders[:10]:  # Limit to top 10
            if reminder.days_overdue == 0:  # Due today or upcoming
                insight = ProactiveInsight(
                    clinic_id=clinic_id,
                    patient_id=reminder.patient_id,
                    doctor_id=None,
                    insight_type=InsightType.FOLLOWUP_DUE.value,
                    priority=reminder.priority,
                    title=f"Follow-up due: {reminder.patient_name}",
                    message=f"{reminder.patient_name} needs {reminder.reason} after {reminder.procedure_type} on {reminder.procedure_date.strftime('%d %b')}",
                    suggested_action={
                        "action": "book_appointment",
                        "patient_id": str(reminder.patient_id),
                        "reason": reminder.reason,
                    },
                    expires_at=datetime.combine(
                        reminder.due_date.date(),
                        datetime.max.time(),
                    ),
                )
                self.db.add(insight)
                insights.append(insight)

        await self.db.commit()

        # Convert to response schemas
        responses = []
        for insight in insights:
            await self.db.refresh(insight)
            responses.append(
                ProactiveInsightResponse.model_validate(insight)
            )

        return responses

    async def find_schedule_gaps(
        self,
        clinic_id: UUID,
        target_date: date,
    ) -> list[ProactiveInsightResponse]:
        """
        Find schedule gaps that could be filled.

        Args:
            clinic_id: Clinic ID
            target_date: Date to analyze

        Returns:
            List of gap insights
        """
        # TODO: Get doctors for clinic
        # For now, skip this implementation
        # Would iterate through doctors and find gaps

        return []

    async def detect_revenue_anomalies(
        self,
        clinic_id: UUID,
        lookback_days: int = 30,
    ) -> list[ProactiveInsightResponse]:
        """
        Detect revenue anomalies.

        Args:
            clinic_id: Clinic ID
            lookback_days: Days to look back for comparison

        Returns:
            List of revenue insights
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        comparison_start = today - timedelta(days=lookback_days)

        # Get yesterday's revenue
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())

        stmt = select(func.sum(Payment.amount)).where(
            and_(
                Payment.clinic_id == clinic_id,
                Payment.payment_date >= yesterday_start,
                Payment.payment_date <= yesterday_end,
                Payment.status == "completed",
            )
        )

        result = await self.db.execute(stmt)
        yesterday_revenue = result.scalar() or 0

        # Get average daily revenue for comparison period
        comp_start_dt = datetime.combine(comparison_start, datetime.min.time())
        comp_end_dt = datetime.combine(yesterday, datetime.max.time())

        stmt = select(func.sum(Payment.amount)).where(
            and_(
                Payment.clinic_id == clinic_id,
                Payment.payment_date >= comp_start_dt,
                Payment.payment_date <= comp_end_dt,
                Payment.status == "completed",
            )
        )

        result = await self.db.execute(stmt)
        total_revenue = result.scalar() or 0
        avg_daily_revenue = total_revenue / lookback_days if lookback_days > 0 else 0

        insights = []

        # Check for significant deviation (> 30%)
        if avg_daily_revenue > 0:
            deviation = ((yesterday_revenue - avg_daily_revenue) / avg_daily_revenue) * 100

            if abs(deviation) > 30:
                priority = InsightPriority.HIGH.value if abs(deviation) > 50 else InsightPriority.MODERATE.value

                if deviation > 0:
                    message = f"Yesterday's revenue (₹{yesterday_revenue:,.0f}) was {deviation:.0f}% above average (₹{avg_daily_revenue:,.0f})"
                    title = "Revenue spike detected"
                else:
                    message = f"Yesterday's revenue (₹{yesterday_revenue:,.0f}) was {abs(deviation):.0f}% below average (₹{avg_daily_revenue:,.0f})"
                    title = "Revenue drop detected"

                insight = ProactiveInsight(
                    clinic_id=clinic_id,
                    insight_type=InsightType.REVENUE_ALERT.value,
                    priority=priority,
                    title=title,
                    message=message,
                    metadata={
                        "yesterday_revenue": float(yesterday_revenue),
                        "avg_revenue": float(avg_daily_revenue),
                        "deviation_percent": deviation,
                    },
                    expires_at=datetime.now() + timedelta(days=2),
                )
                self.db.add(insight)
                insights.append(insight)

        await self.db.commit()

        # Convert to response schemas
        responses = []
        for insight in insights:
            await self.db.refresh(insight)
            responses.append(
                ProactiveInsightResponse.model_validate(insight)
            )

        return responses

    async def identify_no_show_risks(
        self,
        clinic_id: UUID,
        target_date: date,
    ) -> list[ProactiveInsightResponse]:
        """
        Identify appointments with high no-show risk.

        Args:
            clinic_id: Clinic ID
            target_date: Date to analyze

        Returns:
            List of no-show risk insights
        """
        # Get today's appointments
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.clinic_id == clinic_id,
                    Appointment.appointment_date >= start_datetime,
                    Appointment.appointment_date <= end_datetime,
                    Appointment.status.in_(["scheduled", "confirmed"]),
                )
            )
        )

        result = await self.db.execute(stmt)
        appointments = result.scalars().all()

        insights = []

        for appt in appointments:
            # Get patient's no-show history
            patterns = await self.schedule_optimizer.get_patient_appointment_patterns(
                appt.patient_id
            )

            # High risk if no-show rate > 40%
            if patterns["no_show_rate"] > 40 and patterns["total_appointments"] >= 3:
                insight = ProactiveInsight(
                    clinic_id=clinic_id,
                    patient_id=appt.patient_id,
                    doctor_id=appt.doctor_id,
                    insight_type=InsightType.NO_SHOW_RISK.value,
                    priority=InsightPriority.HIGH.value,
                    title=f"High no-show risk",
                    message=f"Patient has {patterns['no_show_rate']:.0f}% no-show rate. Send confirmation reminder.",
                    suggested_action={
                        "action": "send_reminder",
                        "appointment_id": str(appt.id),
                        "patient_id": str(appt.patient_id),
                    },
                    metadata={
                        "appointment_id": str(appt.id),
                        "no_show_rate": patterns["no_show_rate"],
                        "appointment_time": appt.appointment_date.isoformat(),
                    },
                    expires_at=appt.appointment_date,
                )
                self.db.add(insight)
                insights.append(insight)

        await self.db.commit()

        # Convert to response schemas
        responses = []
        for insight in insights:
            await self.db.refresh(insight)
            responses.append(
                ProactiveInsightResponse.model_validate(insight)
            )

        return responses

    async def get_active_insights(
        self,
        clinic_id: UUID,
        insight_types: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[ProactiveInsightResponse]:
        """
        Get active (not dismissed/expired) insights.

        Args:
            clinic_id: Clinic ID
            insight_types: Optional filter by insight types
            limit: Maximum number to return

        Returns:
            List of active insights
        """
        now = datetime.now()

        stmt = (
            select(ProactiveInsight)
            .where(
                and_(
                    ProactiveInsight.clinic_id == clinic_id,
                    ProactiveInsight.dismissed_at.is_(None),
                    ProactiveInsight.acted_at.is_(None),
                    (
                        ProactiveInsight.expires_at.is_(None)
                        | (ProactiveInsight.expires_at > now)
                    ),
                )
            )
            .order_by(
                ProactiveInsight.priority.desc(),
                ProactiveInsight.created_at.desc(),
            )
            .limit(limit)
        )

        if insight_types:
            stmt = stmt.where(ProactiveInsight.insight_type.in_(insight_types))

        result = await self.db.execute(stmt)
        insights = result.scalars().all()

        return [
            ProactiveInsightResponse.model_validate(insight)
            for insight in insights
        ]

    async def dismiss_insight(
        self,
        insight_id: UUID,
        user_id: UUID,
    ) -> ProactiveInsightResponse:
        """
        Dismiss an insight.

        Args:
            insight_id: Insight ID
            user_id: User who dismissed

        Returns:
            Updated insight
        """
        stmt = select(ProactiveInsight).where(ProactiveInsight.id == insight_id)
        result = await self.db.execute(stmt)
        insight = result.scalar_one_or_none()

        if not insight:
            raise ValueError(f"Insight {insight_id} not found")

        insight.dismissed_at = datetime.now()
        insight.dismissed_by_id = user_id

        await self.db.commit()
        await self.db.refresh(insight)

        return ProactiveInsightResponse.model_validate(insight)

    async def act_on_insight(
        self,
        insight_id: UUID,
        user_id: UUID,
    ) -> ProactiveInsightResponse:
        """
        Mark insight as acted upon.

        Args:
            insight_id: Insight ID
            user_id: User who acted

        Returns:
            Updated insight
        """
        stmt = select(ProactiveInsight).where(ProactiveInsight.id == insight_id)
        result = await self.db.execute(stmt)
        insight = result.scalar_one_or_none()

        if not insight:
            raise ValueError(f"Insight {insight_id} not found")

        insight.acted_at = datetime.now()
        insight.acted_by_id = user_id

        await self.db.commit()
        await self.db.refresh(insight)

        return ProactiveInsightResponse.model_validate(insight)
