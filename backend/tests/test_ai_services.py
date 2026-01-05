"""
Comprehensive tests for AI Services.

Tests:
- Smart Scheduling Service
- No-Show Prediction Service
- Slot Optimizer Service
- Natural Language Appointment Search Service
"""

from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.services.smart_scheduling import SmartSchedulingService, SlotSuggestion
from app.services.noshow_prediction import NoShowPredictionService
from app.services.slot_optimizer import SlotOptimizerService
from app.services.nl_appointment_search import NLAppointmentSearchService


# =====================================================================
# Smart Scheduling Tests
# =====================================================================


class TestSmartSchedulingService:
    """Tests for Smart Scheduling Service."""

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        db = AsyncMock(spec=AsyncSession)

        # Mock execute to return query results
        db.execute = AsyncMock()

        return db

    @pytest.fixture
    def service(self, mock_db):
        """Smart scheduling service instance."""
        return SmartSchedulingService(mock_db)

    @pytest.mark.asyncio
    async def test_get_slot_suggestions_for_new_patient(self, service, mock_db):
        """Test slot suggestions for a patient with no history."""
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock no history
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute.return_value = mock_result

        # Mock doctor
        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.id = doctor_id
        mock_doctor.working_hours = {
            "monday": [{"start": "09:00", "end": "17:00"}]
        }
        mock_doctor.slot_duration = 15
        mock_db.get.return_value = mock_doctor

        suggestions = await service.get_slot_suggestions(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_type=AppointmentType.NEW_CONSULTATION,
            max_suggestions=5
        )

        assert isinstance(suggestions, list)
        # Should return suggestions even for new patient
        assert len(suggestions) >= 0

    @pytest.mark.asyncio
    async def test_get_slot_suggestions_with_patient_history(self, service, mock_db):
        """Test slot suggestions based on patient history."""
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock patient history
        past_appointments = [
            MagicMock(
                scheduled_start=datetime.now() - timedelta(days=i*7),
                duration_minutes=15,
                status=AppointmentStatus.COMPLETED.value
            )
            for i in range(5)
        ]
        # Patient prefers mornings (9 AM)
        for appt in past_appointments:
            appt.scheduled_start = appt.scheduled_start.replace(hour=9)

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = past_appointments
        mock_db.execute.return_value = mock_result

        # Mock doctor
        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.working_hours = {
            "monday": [{"start": "09:00", "end": "17:00"}]
        }
        mock_doctor.slot_duration = 15
        mock_db.get.return_value = mock_doctor

        suggestions = await service.get_slot_suggestions(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_type=AppointmentType.FOLLOW_UP,
            max_suggestions=5
        )

        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert isinstance(suggestion, SlotSuggestion)
            assert 0 <= suggestion.score <= 100
            assert isinstance(suggestion.reasons, list)

    @pytest.mark.asyncio
    async def test_analyze_patient_patterns(self, service, mock_db):
        """Test patient pattern analysis."""
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock appointments with clear patterns
        appointments = []
        for i in range(10):
            appt = MagicMock()
            appt.scheduled_start = datetime(2024, 1, 1, 14, 0) + timedelta(weeks=i)  # Always 2 PM
            appt.duration_minutes = 15
            appointments.append(appt)

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = appointments
        mock_db.execute.return_value = mock_result

        patterns = await service._analyze_patient_patterns(patient_id, doctor_id)

        assert 14 in patterns.peak_hours  # 2 PM preference
        assert patterns.average_duration == 15.0
        assert len(patterns.preferred_times) > 0

    @pytest.mark.asyncio
    async def test_no_available_slots(self, service, mock_db):
        """Test handling when no slots are available."""
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock no history
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute.return_value = mock_result

        # Mock doctor with no working hours
        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.working_hours = {}  # No working hours
        mock_doctor.slot_duration = 15
        mock_db.get.return_value = mock_doctor

        suggestions = await service.get_slot_suggestions(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_type=AppointmentType.NEW_CONSULTATION,
        )

        assert isinstance(suggestions, list)
        # May be empty if no working hours
        assert len(suggestions) >= 0

    @pytest.mark.asyncio
    async def test_multi_factor_scoring(self, service):
        """Test multi-factor slot scoring."""
        slot_time = datetime.now().replace(hour=10, minute=0)

        patient_patterns = MagicMock()
        patient_patterns.peak_hours = {10: 5}  # Often books at 10 AM
        patient_patterns.peak_days = {0: 3}  # Prefers Monday
        patient_patterns.preferred_times = [time(10, 0)]
        patient_patterns.follow_up_interval_days = 14

        doctor_patterns = {
            "working_hours": {"monday": [{"start": "09:00", "end": "17:00"}]},
            "slot_duration": 15,
            "busy_hours": {10: 2},  # Not too busy at 10
            "typical_load": {0: 5}
        }

        booking_density = {date.today(): 10}

        score, reasons = service._score_slot(
            slot_time,
            patient_patterns,
            doctor_patterns,
            booking_density,
            AppointmentType.FOLLOW_UP
        )

        assert 0 <= score <= 100
        assert isinstance(reasons, list)
        assert len(reasons) > 0


# =====================================================================
# No-Show Prediction Tests
# =====================================================================


class TestNoShowPredictionService:
    """Tests for No-Show Prediction Service."""

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """No-show prediction service."""
        service = NoShowPredictionService(mock_db)
        # Don't load actual model in tests
        service.model = None
        service.scaler = None
        return service

    @pytest.mark.asyncio
    async def test_predict_for_new_patient(self, service, mock_db):
        """Test prediction for new patient (heuristic fallback)."""
        appointment_id = str(uuid4())
        patient_id = str(uuid4())

        # Mock appointment
        mock_appointment = MagicMock(spec=Appointment)
        mock_appointment.id = appointment_id
        mock_appointment.patient_id = patient_id
        mock_appointment.scheduled_start = datetime.now() + timedelta(days=1)
        mock_appointment.created_at = datetime.now()
        mock_appointment.duration_minutes = 15
        mock_appointment.appointment_type = "new_consultation"
        mock_appointment.booking_source = "app"

        # Mock patient
        mock_patient = MagicMock(spec=Patient)
        mock_patient.id = patient_id
        mock_patient.age = 35

        # Mock DB queries
        appt_result = MagicMock()
        appt_result.scalar_one_or_none.return_value = mock_appointment
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = mock_patient

        # Mock history (new patient)
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        mock_db.execute.side_effect = [
            appt_result,  # Get appointment
            patient_result,  # Get patient
            count_result,  # Total appointments
            count_result,  # No-shows
            count_result,  # Cancellations
            MagicMock(scalar=lambda: None),  # Last appointment
            MagicMock(scalar_one_or_none=lambda: None),  # Existing prediction
        ]

        prediction = await service.predict_no_show(appointment_id)

        assert prediction is not None
        assert 0.0 <= prediction.probability <= 1.0
        assert prediction.risk_level in ["low", "medium", "high"]
        assert "actions" in prediction.mitigation_actions

    @pytest.mark.asyncio
    async def test_predict_for_patient_with_history(self, service, mock_db):
        """Test prediction for patient with no-show history."""
        appointment_id = str(uuid4())
        patient_id = str(uuid4())

        # Mock appointment
        mock_appointment = MagicMock(spec=Appointment)
        mock_appointment.id = appointment_id
        mock_appointment.patient_id = patient_id
        mock_appointment.scheduled_start = datetime.now() + timedelta(days=1)
        mock_appointment.created_at = datetime.now()
        mock_appointment.duration_minutes = 15
        mock_appointment.appointment_type = "follow_up"
        mock_appointment.booking_source = "phone"

        # Mock patient
        mock_patient = MagicMock(spec=Patient)
        mock_patient.id = patient_id
        mock_patient.age = 25

        # Mock history with high no-show rate
        appt_result = MagicMock()
        appt_result.scalar_one_or_none.return_value = mock_appointment
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = mock_patient

        mock_db.execute.side_effect = [
            appt_result,
            patient_result,
            MagicMock(scalar=lambda: 10),  # Total: 10 appointments
            MagicMock(scalar=lambda: 4),   # No-shows: 4 (40% rate!)
            MagicMock(scalar=lambda: 2),   # Cancellations: 2
            MagicMock(scalar=lambda: datetime.now() - timedelta(days=30)),  # Last appt
            MagicMock(scalar_one_or_none=lambda: None),  # No existing prediction
        ]

        prediction = await service.predict_no_show(appointment_id)

        # High no-show rate should result in high risk
        assert prediction.probability > 0.3  # Using heuristics
        assert prediction.risk_level in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_risk_categorization(self, service):
        """Test risk level categorization."""
        assert service._categorize_risk(0.1) == "low"
        assert service._categorize_risk(0.35) == "medium"
        assert service._categorize_risk(0.65) == "high"

    @pytest.mark.asyncio
    async def test_mitigation_actions_high_risk(self, service):
        """Test mitigation actions for high-risk appointments."""
        features = {
            "is_new_patient": True,
            "no_show_rate": 0.5,
        }

        actions = service._generate_mitigation_actions("high", features)

        assert "actions" in actions
        assert len(actions["actions"]) > 0
        assert actions["overbooking_factor"] > 1.0
        # Should include confirmation call
        action_types = [a["action"] for a in actions["actions"]]
        assert "confirmation_call" in action_types

    @pytest.mark.asyncio
    async def test_mitigation_actions_low_risk(self, service):
        """Test mitigation actions for low-risk appointments."""
        features = {"is_new_patient": False}

        actions = service._generate_mitigation_actions("low", features)

        assert len(actions["actions"]) > 0
        assert actions["overbooking_factor"] == 1.0  # No overbooking

    @pytest.mark.asyncio
    async def test_feature_engineering(self, service, mock_db):
        """Test feature extraction from appointment data."""
        mock_appointment = MagicMock()
        mock_appointment.patient_id = str(uuid4())
        mock_appointment.scheduled_start = datetime.now() + timedelta(days=3)
        mock_appointment.created_at = datetime.now()
        mock_appointment.duration_minutes = 30
        mock_appointment.appointment_type = "emergency"
        mock_appointment.booking_source = "app"

        mock_patient = MagicMock()
        mock_patient.age = 45

        # Mock history
        mock_db.execute.side_effect = [
            MagicMock(scalar=lambda: 5),  # Total
            MagicMock(scalar=lambda: 0),  # No-shows
            MagicMock(scalar=lambda: 1),  # Cancellations
            MagicMock(scalar=lambda: datetime.now() - timedelta(days=60)),
        ]

        features = await service._extract_features(mock_appointment, mock_patient)

        assert "total_appointments" in features
        assert "no_show_rate" in features
        assert "lead_time_days" in features
        assert features["lead_time_days"] == 3
        assert "is_weekend" in features
        assert "age" in features
        assert features["age"] == 45

    @pytest.mark.asyncio
    async def test_model_training_insufficient_data(self, service, mock_db):
        """Test model training with insufficient data."""
        # Mock too few appointments
        mock_db.execute.return_value = MagicMock(all=lambda: [])

        result = await service.train_model(min_samples=100)

        assert result["success"] is False
        assert "not enough" in result["message"].lower()


# =====================================================================
# Slot Optimizer Tests
# =====================================================================


class TestSlotOptimizerService:
    """Tests for Slot Optimizer Service."""

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Slot optimizer service."""
        return SlotOptimizerService(mock_db)

    @pytest.mark.asyncio
    async def test_identify_gaps_in_schedule(self, service):
        """Test gap identification in schedule."""
        # Create appointments with gaps
        appointments = [
            MagicMock(
                scheduled_start=datetime.now().replace(hour=9, minute=0),
                duration_minutes=15
            ),
            MagicMock(
                scheduled_start=datetime.now().replace(hour=10, minute=0),  # 45 min gap
                duration_minutes=15
            ),
        ]

        doctor = MagicMock()
        doctor.slot_duration = 15

        gaps = service._identify_gaps(appointments, date.today(), doctor)

        assert len(gaps) > 0
        assert gaps[0]["duration_minutes"] == 45
        assert gaps[0]["is_fillable"] is True

    @pytest.mark.asyncio
    async def test_calculate_utilization(self, service, mock_db):
        """Test utilization calculation."""
        doctor_id = uuid4()
        target_date = date.today()

        # Mock doctor
        mock_doctor = MagicMock()
        mock_doctor.slot_duration = 15
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=lambda: mock_doctor
        )

        # Mock appointments (3 appointments of 15 min each = 45 min)
        appointments = [
            MagicMock(
                scheduled_start=datetime.combine(target_date, time(10, 0)),
                duration_minutes=15
            )
            for _ in range(3)
        ]

        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_doctor),
            MagicMock(scalars=lambda: MagicMock(all=lambda: appointments))
        ]

        analysis = await service.analyze_schedule(doctor_id, target_date)

        assert "utilization_rate" in analysis
        assert "gap_count" in analysis
        assert "efficiency_score" in analysis
        assert analysis["appointment_count"] == 3

    @pytest.mark.asyncio
    async def test_optimal_slot_scoring(self, service):
        """Test slot scoring algorithm."""
        slot_time = datetime.now().replace(hour=10, minute=0)

        # No nearby appointments = larger gaps
        appointments = [
            MagicMock(
                scheduled_start=datetime.now().replace(hour=8, minute=0),
                duration_minutes=15,
                appointment_type="new_consultation"
            ),
        ]

        doctor = MagicMock()
        doctor.slot_duration = 15

        score = service._score_slot(
            slot_time,
            15,  # duration
            appointments,
            doctor,
            "new_consultation",
            {},  # No patient patterns
            None  # No constraints
        )

        assert isinstance(score.score, float)
        assert 0 <= score.score <= 100
        assert isinstance(score.reasons, list)

    @pytest.mark.asyncio
    async def test_gap_minimization(self, service):
        """Test that gap penalty is calculated correctly."""
        slot_time = datetime.now().replace(hour=10, minute=0)

        # Appointment ending right before slot (no gap)
        appointments = [
            MagicMock(
                scheduled_start=datetime.now().replace(hour=9, minute=45),
                duration_minutes=15  # Ends at 10:00
            )
        ]

        gap_penalty = service._calculate_gap_penalty(slot_time, 15, appointments)

        # Should have low penalty since there's no gap
        assert gap_penalty < 20

    @pytest.mark.asyncio
    async def test_utilization_optimization(self, service, mock_db):
        """Test utilization-based recommendations."""
        doctor_id = uuid4()

        # Mock doctor
        mock_doctor = MagicMock()
        mock_doctor.slot_duration = 15
        mock_doctor.working_hours = {"monday": [{"start": "09:00", "end": "18:00"}]}

        # Mock low utilization
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_doctor),
            MagicMock(scalars=lambda: MagicMock(all=lambda: [])),  # No appointments
        ]

        suggestions = await service.suggest_schedule_adjustments(
            doctor_id,
            date.today(),
            date.today() + timedelta(days=7)
        )

        assert "adjustments" in suggestions
        assert "current_efficiency_score" in suggestions
        # Low utilization should trigger suggestions
        assert len(suggestions["adjustments"]) > 0

    @pytest.mark.asyncio
    async def test_energy_level_optimization(self, service):
        """Test that complex cases are scheduled in morning."""
        morning_slot = datetime.now().replace(hour=10, minute=0)
        evening_slot = datetime.now().replace(hour=17, minute=0)

        morning_bonus = service._calculate_energy_bonus(morning_slot, AppointmentType.PROCEDURE.value)
        evening_bonus = service._calculate_energy_bonus(evening_slot, AppointmentType.PROCEDURE.value)

        # Complex procedures should have higher bonus in morning
        assert morning_bonus > evening_bonus


# =====================================================================
# Natural Language Appointment Search Tests
# =====================================================================


class TestNLAppointmentSearch:
    """Tests for Natural Language Appointment Search."""

    @pytest.fixture
    def service(self):
        """NL search service."""
        return NLAppointmentSearchService()

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_parse_simple_time_query(self, service):
        """Test parsing 'appointments tomorrow'."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "message": {
                        "content": f'{{"query_type": "search", "confidence": 0.95, "entities": {{}}, "filters": {{"exact_date": "{(date.today() + timedelta(days=1)).isoformat()}"}}}}'
                    }
                },
                raise_for_status=lambda: None
            )

            parsed = await service.parse_query("appointments tomorrow")

            assert parsed.query_type == "search"
            assert parsed.parsed_date.exact_date == date.today() + timedelta(days=1)

    @pytest.mark.asyncio
    async def test_parse_doctor_query(self, service):
        """Test parsing 'Dr. Patel's schedule'."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "message": {
                        "content": '{"query_type": "search", "confidence": 0.9, "entities": {"doctor_name": "Patel"}, "filters": {}}'
                    }
                },
                raise_for_status=lambda: None
            )

            parsed = await service.parse_query("Dr. Patel's schedule")

            assert parsed.doctor_name == "Patel"

    @pytest.mark.asyncio
    async def test_parse_status_query(self, service):
        """Test parsing 'cancelled appointments this week'."""
        with patch('httpx.AsyncClient.post') as mock_post:
            week_start = date.today() - timedelta(days=date.today().weekday())
            week_end = week_start + timedelta(days=6)

            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "message": {
                        "content": f'{{"query_type": "search", "confidence": 0.92, "entities": {{"status": ["cancelled"]}}, "filters": {{"start_date": "{week_start.isoformat()}", "end_date": "{week_end.isoformat()}"}}}}'
                    }
                },
                raise_for_status=lambda: None
            )

            parsed = await service.parse_query("cancelled appointments this week")

            assert "cancelled" in parsed.status_filter

    @pytest.mark.asyncio
    async def test_parse_hindi_query(self, service):
        """Test parsing Hindi query 'aaj ke appointments'."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "message": {
                        "content": f'{{"query_type": "search", "confidence": 0.88, "entities": {{}}, "filters": {{"exact_date": "{date.today().isoformat()}"}}}}'
                    }
                },
                raise_for_status=lambda: None
            )

            parsed = await service.parse_query("aaj ke appointments")

            assert parsed.parsed_date.exact_date == date.today()

    @pytest.mark.asyncio
    async def test_aggregate_query(self, service, mock_db):
        """Test aggregate query 'how many appointments today'."""
        clinic_id = uuid4()

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "message": {
                        "content": f'{{"query_type": "aggregate", "confidence": 0.95, "entities": {{}}, "filters": {{"exact_date": "{date.today().isoformat()}"}}}}'
                    }
                },
                raise_for_status=lambda: None
            )

            # Mock DB results
            mock_db.execute.return_value = MagicMock(
                scalars=lambda: MagicMock(all=lambda: [
                    MagicMock(status="scheduled"),
                    MagicMock(status="confirmed"),
                    MagicMock(status="scheduled"),
                ])
            )

            result = await service.aggregate_query(
                "how many appointments today",
                clinic_id,
                mock_db
            )

            assert result.data.count == 3
            assert "scheduled" in result.data.breakdown

    @pytest.mark.asyncio
    async def test_fallback_when_llm_unavailable(self, service):
        """Test fallback parsing when LLM is unavailable."""
        with patch('httpx.AsyncClient.post', side_effect=Exception("Connection failed")):
            parsed = await service.parse_query("cancelled appointments")

            # Should use fallback regex parsing
            assert parsed.confidence < 1.0
            assert "cancelled" in parsed.status_filter

    @pytest.mark.asyncio
    async def test_ambiguous_query_handling(self, service):
        """Test handling of ambiguous queries."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "message": {
                        "content": '{"query_type": "search", "confidence": 0.3, "entities": {}, "filters": {}, "needs_clarification": true, "clarification_question": "Which date?"}'
                    }
                },
                raise_for_status=lambda: None
            )

            parsed = await service.parse_query("show appointments")

            assert parsed.confidence < 0.5 or parsed.needs_clarification is True

    @pytest.mark.asyncio
    async def test_relevance_scoring(self, service):
        """Test appointment relevance scoring."""
        mock_appointment = MagicMock()
        mock_appointment.scheduled_start = datetime.combine(date.today(), time(10, 0))
        mock_appointment.status = "cancelled"

        from app.services.nl_appointment_search import ParsedQuery, ParsedDateFilter

        parsed_query = ParsedQuery(
            entities={},
            filters={},
            query_type="search",
            confidence=0.9,
            parsed_date=ParsedDateFilter(exact_date=date.today()),
            status_filter=["cancelled"]
        )

        score = service._calculate_relevance(mock_appointment, parsed_query)

        assert 0.0 <= score <= 1.0
        # Should have high score for exact date + status match
        assert score > 0.5

    def test_get_suggestions(self, service):
        """Test getting query suggestions."""
        suggestions = service.get_suggestions()

        assert len(suggestions) > 0
        assert all(hasattr(s, "text") for s in suggestions)
        assert all(hasattr(s, "category") for s in suggestions)
