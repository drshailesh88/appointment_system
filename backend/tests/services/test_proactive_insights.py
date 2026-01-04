"""
Tests for Proactive Insights Service.

Phase 16c: Practice AI - Proactive Intelligence
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.insight import InsightType, InsightPriority, ProactiveInsight
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.procedure import Procedure, ProcedureOutcome
from app.models.user import User
from app.services.followup_intelligence import FollowupIntelligence
from app.services.proactive_insights import ProactiveInsightsEngine
from app.services.schedule_optimizer import ScheduleOptimizer


class TestFollowupIntelligence:
    """Test follow-up intelligence service."""

    @pytest.mark.asyncio
    async def test_suggest_followups_after_stent(self, db_session: AsyncSession):
        """Test follow-up suggestions after stent placement."""
        # Create test procedure
        procedure = Procedure(
            id=uuid4(),
            clinic_id=uuid4(),
            patient_id=uuid4(),
            doctor_id=uuid4(),
            category="Cardiology",
            procedure_type="Stent Placement",
            name="Drug-Eluting Stent",
            performed_at=datetime.now(),
            outcome=ProcedureOutcome.SUCCESSFUL.value,
        )

        intelligence = FollowupIntelligence(db_session)
        suggestions = await intelligence.suggest_followups_after_procedure(procedure)

        # Should suggest 3 follow-ups: 7 days, 30 days, 180 days
        assert len(suggestions) == 3
        assert suggestions[0].days_from_procedure == 7
        assert suggestions[0].reason == "Post-stent check"
        assert suggestions[0].priority == 5  # Urgent

        assert suggestions[1].days_from_procedure == 30
        assert suggestions[2].days_from_procedure == 180

    @pytest.mark.asyncio
    async def test_suggest_followups_after_cataract(self, db_session: AsyncSession):
        """Test follow-up suggestions after cataract surgery."""
        procedure = Procedure(
            id=uuid4(),
            clinic_id=uuid4(),
            patient_id=uuid4(),
            doctor_id=uuid4(),
            category="Ophthalmology",
            procedure_type="Cataract Surgery",
            name="Phacoemulsification",
            performed_at=datetime.now(),
            outcome=ProcedureOutcome.SUCCESSFUL.value,
        )

        intelligence = FollowupIntelligence(db_session)
        suggestions = await intelligence.suggest_followups_after_procedure(procedure)

        # Should suggest 3 follow-ups: 1 day, 7 days, 30 days
        assert len(suggestions) == 3
        assert suggestions[0].days_from_procedure == 1
        assert suggestions[0].reason == "Day-1 post-op check"

    @pytest.mark.asyncio
    async def test_conditional_followup_for_abnormal_echo(self, db_session: AsyncSession):
        """Test conditional follow-up for echo with abnormal findings."""
        procedure = Procedure(
            id=uuid4(),
            clinic_id=uuid4(),
            patient_id=uuid4(),
            doctor_id=uuid4(),
            category="Cardiology",
            procedure_type="Echocardiogram",
            name="2D Echo",
            performed_at=datetime.now(),
            outcome=ProcedureOutcome.SUCCESSFUL.value,
            custom_fields={"ef": 35},  # EF below 40
            findings="Reduced ejection fraction, mild LV dysfunction",
        )

        intelligence = FollowupIntelligence(db_session)
        suggestions = await intelligence.suggest_followups_after_procedure(procedure)

        # Should suggest follow-up since EF < 40
        assert len(suggestions) == 1
        assert suggestions[0].days_from_procedure == 180
        assert "repeat echo" in suggestions[0].reason.lower()

    @pytest.mark.asyncio
    async def test_no_followup_for_normal_echo(self, db_session: AsyncSession):
        """Test no follow-up for echo with normal findings."""
        procedure = Procedure(
            id=uuid4(),
            clinic_id=uuid4(),
            patient_id=uuid4(),
            doctor_id=uuid4(),
            category="Cardiology",
            procedure_type="Echocardiogram",
            name="2D Echo",
            performed_at=datetime.now(),
            outcome=ProcedureOutcome.SUCCESSFUL.value,
            custom_fields={"ef": 60},  # Normal EF
            findings="Normal cardiac function",
        )

        intelligence = FollowupIntelligence(db_session)
        suggestions = await intelligence.suggest_followups_after_procedure(procedure)

        # Should not suggest follow-up since EF is normal
        assert len(suggestions) == 0


class TestScheduleOptimizer:
    """Test schedule optimization service."""

    @pytest.mark.asyncio
    async def test_find_gaps_in_schedule(self, db_session: AsyncSession):
        """Test finding gaps in doctor's schedule."""
        clinic_id = uuid4()
        doctor_id = uuid4()
        target_date = date.today()

        # Create appointments with gaps
        appointments = [
            Appointment(
                id=uuid4(),
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                patient_id=uuid4(),
                appointment_date=datetime.combine(target_date, datetime.min.time().replace(hour=10)),
                duration_minutes=30,
                status="scheduled",
            ),
            Appointment(
                id=uuid4(),
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                patient_id=uuid4(),
                appointment_date=datetime.combine(target_date, datetime.min.time().replace(hour=12)),
                duration_minutes=30,
                status="scheduled",
            ),
        ]

        for appt in appointments:
            db_session.add(appt)
        await db_session.commit()

        optimizer = ScheduleOptimizer(db_session)
        gaps = await optimizer.find_gaps(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            target_date=target_date,
            min_gap_minutes=30,
        )

        # Should find gap between 9 AM - 10 AM, 10:30 AM - 12 PM, and 12:30 PM - 6 PM
        assert len(gaps) >= 2

    @pytest.mark.asyncio
    async def test_overbooking_risk_detection(self, db_session: AsyncSession):
        """Test overbooking risk detection."""
        clinic_id = uuid4()
        doctor_id = uuid4()
        target_date = date.today()

        # Create many appointments to simulate overbooking
        for i in range(20):
            appt = Appointment(
                id=uuid4(),
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                patient_id=uuid4(),
                appointment_date=datetime.combine(
                    target_date,
                    datetime.min.time().replace(hour=9 + (i // 4), minute=(i % 4) * 15),
                ),
                duration_minutes=30,
                status="scheduled",
            )
            db_session.add(appt)
        await db_session.commit()

        optimizer = ScheduleOptimizer(db_session)
        risk = await optimizer.analyze_overbooking_risk(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            target_date=target_date,
        )

        # With 20 appointments of 30 min each = 600 minutes > 540 available
        assert risk.risk_level == "high"
        assert risk.estimated_duration_minutes > risk.available_minutes


class TestProactiveInsightsEngine:
    """Test proactive insights engine."""

    @pytest.mark.asyncio
    async def test_revenue_anomaly_detection(self, db_session: AsyncSession):
        """Test revenue anomaly detection."""
        clinic_id = uuid4()

        # Create historical payments (average ~10,000/day)
        for i in range(30):
            payment = Payment(
                id=uuid4(),
                clinic_id=clinic_id,
                patient_id=uuid4(),
                amount=Decimal("10000"),
                payment_date=datetime.now() - timedelta(days=i+2),
                status="completed",
                payment_method="cash",
            )
            db_session.add(payment)

        # Create yesterday's payment (very low - anomaly)
        low_payment = Payment(
            id=uuid4(),
            clinic_id=clinic_id,
            patient_id=uuid4(),
            amount=Decimal("2000"),  # 80% below average
            payment_date=datetime.now() - timedelta(days=1),
            status="completed",
            payment_method="cash",
        )
        db_session.add(low_payment)
        await db_session.commit()

        engine = ProactiveInsightsEngine(db_session)
        insights = await engine.detect_revenue_anomalies(clinic_id=clinic_id)

        # Should detect revenue drop
        assert len(insights) > 0
        revenue_insight = insights[0]
        assert revenue_insight.insight_type == InsightType.REVENUE_ALERT.value
        assert "below" in revenue_insight.message.lower()

    @pytest.mark.asyncio
    async def test_no_show_risk_identification(self, db_session: AsyncSession):
        """Test no-show risk identification."""
        clinic_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()

        # Create patient with high no-show history
        for i in range(5):
            appt = Appointment(
                id=uuid4(),
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                patient_id=patient_id,
                appointment_date=datetime.now() - timedelta(days=i+7),
                status="no_show" if i < 3 else "completed",  # 60% no-show rate
            )
            db_session.add(appt)

        # Create today's appointment for same patient
        today_appt = Appointment(
            id=uuid4(),
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            appointment_date=datetime.now(),
            status="scheduled",
        )
        db_session.add(today_appt)
        await db_session.commit()

        engine = ProactiveInsightsEngine(db_session)
        insights = await engine.identify_no_show_risks(
            clinic_id=clinic_id,
            target_date=date.today(),
        )

        # Should identify high no-show risk
        assert len(insights) > 0
        risk_insight = insights[0]
        assert risk_insight.insight_type == InsightType.NO_SHOW_RISK.value
        assert risk_insight.priority == InsightPriority.HIGH.value

    @pytest.mark.asyncio
    async def test_dismiss_insight(self, db_session: AsyncSession):
        """Test dismissing an insight."""
        clinic_id = uuid4()
        user_id = uuid4()

        # Create insight
        insight = ProactiveInsight(
            id=uuid4(),
            clinic_id=clinic_id,
            insight_type=InsightType.FOLLOWUP_DUE.value,
            priority=InsightPriority.MEDIUM.value,
            title="Test Insight",
            message="Test message",
        )
        db_session.add(insight)
        await db_session.commit()

        engine = ProactiveInsightsEngine(db_session)
        dismissed = await engine.dismiss_insight(
            insight_id=insight.id,
            user_id=user_id,
        )

        assert dismissed.dismissed_at is not None
        assert dismissed.dismissed_by_id == user_id

    @pytest.mark.asyncio
    async def test_act_on_insight(self, db_session: AsyncSession):
        """Test acting on an insight."""
        clinic_id = uuid4()
        user_id = uuid4()

        # Create insight with suggested action
        insight = ProactiveInsight(
            id=uuid4(),
            clinic_id=clinic_id,
            insight_type=InsightType.FOLLOWUP_DUE.value,
            priority=InsightPriority.MEDIUM.value,
            title="Book Follow-up",
            message="Patient needs follow-up",
            suggested_action={
                "action": "book_appointment",
                "patient_id": str(uuid4()),
            },
        )
        db_session.add(insight)
        await db_session.commit()

        engine = ProactiveInsightsEngine(db_session)
        acted = await engine.act_on_insight(
            insight_id=insight.id,
            user_id=user_id,
        )

        assert acted.acted_at is not None
        assert acted.acted_by_id == user_id


# Pytest fixtures (would be in conftest.py in actual implementation)

@pytest.fixture
async def db_session():
    """Mock database session."""
    # This would be a real test database session
    # For now, returning a mock
    from unittest.mock import AsyncMock
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = lambda x: None
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session
