"""
Slot Optimizer Service.

AI-powered scheduling optimization that recommends the best available slots
to maximize clinic efficiency and patient satisfaction.

Key Features:
- Minimize gaps between appointments
- Balance workload across day
- Cluster similar appointment types
- Consider buffer time needs
- Factor in doctor energy levels
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.doctor import Doctor
from app.models.patient import Patient

logger = logging.getLogger(__name__)


@dataclass
class SlotScore:
    """Internal slot scoring data."""

    slot_time: datetime
    score: float
    gap_penalty: float
    utilization_bonus: float
    type_match_bonus: float
    energy_bonus: float
    reasons: list[str]
    nearby_types: list[str]


class SlotOptimizerService:
    """
    Slot optimization service.

    Uses AI-driven algorithms to recommend optimal appointment slots.
    """

    # Scoring weights
    WEIGHT_GAP_PENALTY = 0.3
    WEIGHT_UTILIZATION = 0.3
    WEIGHT_TYPE_CLUSTERING = 0.2
    WEIGHT_ENERGY_LEVEL = 0.2

    # Time constants
    IDEAL_GAP_MINUTES = 0  # No gap is ideal
    MAX_GAP_MINUTES = 60  # Gaps longer than 1hr are very inefficient
    WORKING_HOURS_START = time(9, 0)
    WORKING_HOURS_END = time(18, 0)

    def __init__(self, db: AsyncSession):
        """Initialize optimizer service with database session."""
        self.db = db

    async def get_optimal_slots(
        self,
        doctor_id: UUID,
        date_range_start: date,
        date_range_end: date,
        duration_minutes: int = 15,
        appointment_type: Optional[str] = None,
        patient_id: Optional[UUID] = None,
        max_recommendations: int = 5,
        constraints: Optional[dict] = None,
    ) -> list[SlotScore]:
        """
        Get optimal available slots for a doctor.

        Args:
            doctor_id: Doctor to schedule with
            date_range_start: Start of date range
            date_range_end: End of date range
            duration_minutes: Appointment duration
            appointment_type: Type of appointment (for clustering)
            patient_id: Patient for preference matching
            max_recommendations: Number of slots to return
            constraints: Patient availability constraints

        Returns:
            List of scored slots, sorted by score (descending)
        """
        # Get doctor info
        doctor = await self._get_doctor(doctor_id)
        if not doctor:
            return []

        # Get existing appointments
        appointments = await self._get_appointments(
            doctor_id,
            date_range_start,
            date_range_end,
        )

        # Get patient history if available
        patient_patterns = {}
        if patient_id:
            patient_patterns = await self._get_patient_patterns(patient_id)

        # Generate available slots
        all_slots = self._generate_available_slots(
            doctor,
            date_range_start,
            date_range_end,
            duration_minutes,
            appointments,
        )

        # Score each slot
        scored_slots = []
        for slot_time in all_slots:
            score = self._score_slot(
                slot_time,
                duration_minutes,
                appointments,
                doctor,
                appointment_type,
                patient_patterns,
                constraints,
            )
            scored_slots.append(score)

        # Sort by score and return top N
        scored_slots.sort(key=lambda s: s.score, reverse=True)
        return scored_slots[:max_recommendations]

    async def analyze_schedule(
        self,
        doctor_id: UUID,
        target_date: date,
    ) -> dict:
        """
        Analyze current schedule efficiency.

        Args:
            doctor_id: Doctor to analyze
            target_date: Date to analyze

        Returns:
            Analysis with utilization, gaps, and suggestions
        """
        doctor = await self._get_doctor(doctor_id)
        if not doctor:
            return {}

        # Get appointments for the day
        appointments = await self._get_appointments(
            doctor_id,
            target_date,
            target_date,
        )

        # Calculate metrics
        working_minutes = self._calculate_working_minutes(doctor)
        gaps = self._identify_gaps(appointments, target_date, doctor)
        total_gap_minutes = sum(g["duration_minutes"] for g in gaps)
        booked_minutes = sum(a.duration_minutes for a in appointments)

        utilization_rate = (
            (booked_minutes / working_minutes * 100) if working_minutes > 0 else 0.0
        )

        # Calculate efficiency score
        gap_penalty = min(total_gap_minutes / working_minutes * 100, 50)
        efficiency_score = max(0, utilization_rate - gap_penalty)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            utilization_rate,
            gaps,
            appointments,
            doctor,
        )

        return {
            "utilization_rate": round(utilization_rate, 2),
            "gap_count": len(gaps),
            "total_gap_minutes": total_gap_minutes,
            "longest_gap_minutes": max((g["duration_minutes"] for g in gaps), default=0),
            "appointment_count": len(appointments),
            "working_hours": working_minutes // 60,
            "efficiency_score": round(efficiency_score, 2),
            "gaps": gaps,
            "suggestions": suggestions,
        }

    async def get_utilization_metrics(
        self,
        doctor_id: UUID,
        date_range_start: date,
        date_range_end: date,
    ) -> dict:
        """
        Get detailed utilization metrics.

        Args:
            doctor_id: Doctor to analyze
            date_range_start: Start of range
            date_range_end: End of range

        Returns:
            Metrics by hour and day of week
        """
        doctor = await self._get_doctor(doctor_id)
        if not doctor:
            return {}

        appointments = await self._get_appointments(
            doctor_id,
            date_range_start,
            date_range_end,
        )

        # Metrics by hour
        by_hour = defaultdict(lambda: {"booked": 0, "available": 0, "gap_minutes": 0})
        for appt in appointments:
            hour = appt.scheduled_start.hour
            by_hour[hour]["booked"] += 1

        # Calculate available slots per hour (rough estimate)
        slot_duration = doctor.slot_duration or 15
        slots_per_hour = 60 // slot_duration
        days_in_period = (date_range_end - date_range_start).days + 1

        hour_metrics = []
        for hour in range(9, 18):  # 9 AM to 6 PM
            booked = by_hour[hour]["booked"]
            available = slots_per_hour * days_in_period
            util_rate = (booked / available * 100) if available > 0 else 0
            hour_metrics.append({
                "label": f"{hour:02d}:00",
                "utilization_rate": round(util_rate, 2),
                "booked_slots": booked,
                "available_slots": available,
                "gap_minutes": 0,  # Would need gap analysis
            })

        # Metrics by day of week
        by_day = defaultdict(lambda: {"booked": 0, "available": 0})
        for appt in appointments:
            day = appt.scheduled_start.weekday()
            by_day[day]["booked"] += 1

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_metrics = []
        for day_idx, day_name in enumerate(day_names):
            booked = by_day[day_idx]["booked"]
            # Count how many of this weekday in range
            day_count = sum(
                1
                for d in range(days_in_period)
                if (date_range_start + timedelta(days=d)).weekday() == day_idx
            )
            available = slots_per_hour * 9 * day_count  # 9 working hours
            util_rate = (booked / available * 100) if available > 0 else 0
            day_metrics.append({
                "label": day_name,
                "utilization_rate": round(util_rate, 2),
                "booked_slots": booked,
                "available_slots": available,
                "gap_minutes": 0,
            })

        # Overall utilization
        total_booked = len(appointments)
        total_available = slots_per_hour * 9 * days_in_period
        overall_util = (total_booked / total_available * 100) if total_available > 0 else 0

        # Find peak and low hours
        sorted_hours = sorted(hour_metrics, key=lambda h: h["utilization_rate"], reverse=True)
        peak_hours = [int(h["label"].split(":")[0]) for h in sorted_hours[:3]]
        low_hours = [int(h["label"].split(":")[0]) for h in sorted_hours[-3:]]

        return {
            "by_hour": hour_metrics,
            "by_day": day_metrics,
            "overall_utilization": round(overall_util, 2),
            "peak_hours": peak_hours,
            "low_hours": low_hours,
            "trends": {},
        }

    async def suggest_schedule_adjustments(
        self,
        doctor_id: UUID,
        date_range_start: date,
        date_range_end: date,
    ) -> dict:
        """
        Suggest schedule optimizations.

        Args:
            doctor_id: Doctor to optimize for
            date_range_start: Analysis start date
            date_range_end: Analysis end date

        Returns:
            Optimization suggestions with expected improvements
        """
        doctor = await self._get_doctor(doctor_id)
        if not doctor:
            return {}

        # Get metrics
        metrics = await self.get_utilization_metrics(
            doctor_id,
            date_range_start,
            date_range_end,
        )

        # Analyze and suggest
        adjustments = []
        current_util = metrics.get("overall_utilization", 0)

        # Suggest slot duration adjustments
        if current_util < 60:
            adjustments.append({
                "adjustment_type": "slot_duration",
                "current_value": doctor.slot_duration or 15,
                "suggested_value": max(10, (doctor.slot_duration or 15) - 5),
                "reason": "Shorter slots could improve availability and utilization",
                "expected_improvement": 15.0,
                "priority": "medium",
            })

        # Suggest working hours adjustment for low utilization
        if current_util < 50:
            adjustments.append({
                "adjustment_type": "working_hours",
                "current_value": "9:00 - 18:00",
                "suggested_value": "10:00 - 16:00",
                "reason": "Focus on peak hours to improve efficiency",
                "expected_improvement": 20.0,
                "priority": "high",
            })

        # Suggest focusing on peak hours
        peak_hours = metrics.get("peak_hours", [])
        if peak_hours:
            adjustments.append({
                "adjustment_type": "capacity",
                "current_value": "uniform",
                "suggested_value": f"Increase capacity at {peak_hours} hours",
                "reason": f"Hours {peak_hours} show highest demand",
                "expected_improvement": 10.0,
                "priority": "medium",
            })

        potential_score = min(100, current_util + sum(a["expected_improvement"] for a in adjustments))

        return {
            "current_efficiency_score": round(current_util, 2),
            "potential_efficiency_score": round(potential_score, 2),
            "adjustments": adjustments,
            "summary": f"Implementing {len(adjustments)} adjustments could improve efficiency by {round(potential_score - current_util, 1)}%",
            "estimated_impact": {
                "utilization_increase": round(potential_score - current_util, 1),
                "additional_appointments_per_week": int((potential_score - current_util) / 100 * 50),
            },
        }

    # Private helper methods

    async def _get_doctor(self, doctor_id: UUID) -> Optional[Doctor]:
        """Get doctor by ID."""
        result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        return result.scalar_one_or_none()

    async def _get_appointments(
        self,
        doctor_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[Appointment]:
        """Get appointments for doctor in date range."""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        result = await self.db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.scheduled_start >= start_dt,
                    Appointment.scheduled_start <= end_dt,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED.value,
                        AppointmentStatus.CONFIRMED.value,
                        AppointmentStatus.CHECKED_IN.value,
                    ]),
                )
            )
            .order_by(Appointment.scheduled_start)
        )
        return list(result.scalars().all())

    async def _get_patient_patterns(self, patient_id: UUID) -> dict:
        """Get patient scheduling patterns."""
        # Get patient's historical appointments
        result = await self.db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.status == AppointmentStatus.COMPLETED.value,
                )
            )
            .order_by(Appointment.scheduled_start.desc())
            .limit(10)
        )
        past_appointments = list(result.scalars().all())

        if not past_appointments:
            return {}

        # Analyze patterns
        preferred_hours = defaultdict(int)
        preferred_days = defaultdict(int)

        for appt in past_appointments:
            preferred_hours[appt.scheduled_start.hour] += 1
            preferred_days[appt.scheduled_start.weekday()] += 1

        return {
            "preferred_hours": dict(preferred_hours),
            "preferred_days": dict(preferred_days),
        }

    def _generate_available_slots(
        self,
        doctor: Doctor,
        start_date: date,
        end_date: date,
        duration_minutes: int,
        existing_appointments: list[Appointment],
    ) -> list[datetime]:
        """Generate all available time slots."""
        available_slots = []
        slot_duration = doctor.slot_duration or 15

        current_date = start_date
        while current_date <= end_date:
            # Generate slots for this day
            current_time = datetime.combine(current_date, self.WORKING_HOURS_START)
            end_time = datetime.combine(current_date, self.WORKING_HOURS_END)

            while current_time < end_time:
                # Check if slot is available
                if self._is_slot_available(current_time, duration_minutes, existing_appointments):
                    available_slots.append(current_time)

                current_time += timedelta(minutes=slot_duration)

            current_date += timedelta(days=1)

        return available_slots

    def _is_slot_available(
        self,
        slot_time: datetime,
        duration_minutes: int,
        appointments: list[Appointment],
    ) -> bool:
        """Check if a slot is available."""
        slot_end = slot_time + timedelta(minutes=duration_minutes)

        for appt in appointments:
            appt_end = appt.scheduled_start + timedelta(minutes=appt.duration_minutes)

            # Check for overlap
            if (slot_time < appt_end) and (slot_end > appt.scheduled_start):
                return False

        return True

    def _score_slot(
        self,
        slot_time: datetime,
        duration_minutes: int,
        appointments: list[Appointment],
        doctor: Doctor,
        appointment_type: Optional[str],
        patient_patterns: dict,
        constraints: Optional[dict],
    ) -> SlotScore:
        """Score a potential slot."""
        reasons = []
        nearby_types = []

        # 1. Gap penalty - prefer slots that minimize gaps
        gap_penalty = self._calculate_gap_penalty(slot_time, duration_minutes, appointments)
        if gap_penalty < 10:
            reasons.append("Minimizes schedule gaps")

        # 2. Utilization bonus - prefer slots that improve daily utilization
        utilization_bonus = self._calculate_utilization_bonus(slot_time, appointments)
        if utilization_bonus > 20:
            reasons.append("Improves daily utilization")

        # 3. Type clustering - prefer slots near similar appointment types
        type_match_bonus = 0
        if appointment_type:
            type_match_bonus, nearby_types = self._calculate_type_clustering(
                slot_time,
                appointment_type,
                appointments,
            )
            if type_match_bonus > 15:
                reasons.append(f"Near other {appointment_type} appointments")

        # 4. Energy level - prefer complex cases early, simple cases late
        energy_bonus = self._calculate_energy_bonus(slot_time, appointment_type)
        if energy_bonus > 15:
            reasons.append("Optimal time for this appointment type")

        # 5. Patient preference match
        if patient_patterns:
            pref_hour = slot_time.hour
            if pref_hour in patient_patterns.get("preferred_hours", {}):
                reasons.append("Matches patient's usual appointment time")
                utilization_bonus += 10

        # Calculate final score
        score = (
            self.WEIGHT_GAP_PENALTY * (100 - gap_penalty)
            + self.WEIGHT_UTILIZATION * utilization_bonus
            + self.WEIGHT_TYPE_CLUSTERING * type_match_bonus
            + self.WEIGHT_ENERGY_LEVEL * energy_bonus
        )

        return SlotScore(
            slot_time=slot_time,
            score=min(100, score),
            gap_penalty=gap_penalty,
            utilization_bonus=utilization_bonus,
            type_match_bonus=type_match_bonus,
            energy_bonus=energy_bonus,
            reasons=reasons if reasons else ["Available slot"],
            nearby_types=nearby_types,
        )

    def _calculate_gap_penalty(
        self,
        slot_time: datetime,
        duration_minutes: int,
        appointments: list[Appointment],
    ) -> float:
        """Calculate penalty for creating gaps."""
        if not appointments:
            return 0.0

        slot_end = slot_time + timedelta(minutes=duration_minutes)

        # Find nearest appointments before and after
        before_gap = None
        after_gap = None

        for appt in appointments:
            appt_end = appt.scheduled_start + timedelta(minutes=appt.duration_minutes)

            if appt_end <= slot_time:
                gap = (slot_time - appt_end).total_seconds() / 60
                if before_gap is None or gap < before_gap:
                    before_gap = gap

            if appt.scheduled_start >= slot_end:
                gap = (appt.scheduled_start - slot_end).total_seconds() / 60
                if after_gap is None or gap < after_gap:
                    after_gap = gap

        # Calculate penalty based on gaps
        total_gap = 0
        if before_gap is not None:
            total_gap += max(0, before_gap - self.IDEAL_GAP_MINUTES)
        if after_gap is not None:
            total_gap += max(0, after_gap - self.IDEAL_GAP_MINUTES)

        # Normalize to 0-100 scale
        penalty = min(100, (total_gap / self.MAX_GAP_MINUTES) * 100)
        return penalty

    def _calculate_utilization_bonus(
        self,
        slot_time: datetime,
        appointments: list[Appointment],
    ) -> float:
        """Calculate bonus for improving utilization."""
        # Count appointments on the same day
        same_day_appts = [
            a for a in appointments
            if a.scheduled_start.date() == slot_time.date()
        ]

        # More appointments in the day = higher utilization
        current_count = len(same_day_appts)

        # Ideal is around 20-30 appointments per day (depends on slot duration)
        ideal_count = 25
        if current_count < ideal_count:
            # Bonus for filling the day
            bonus = min(100, ((current_count + 1) / ideal_count) * 100)
        else:
            # Penalty for overloading
            bonus = max(0, 100 - ((current_count - ideal_count) * 5))

        return bonus

    def _calculate_type_clustering(
        self,
        slot_time: datetime,
        appointment_type: str,
        appointments: list[Appointment],
    ) -> tuple[float, list[str]]:
        """Calculate bonus for appointment type clustering."""
        nearby_window = timedelta(hours=2)
        nearby_types = []

        # Find appointments within 2-hour window
        for appt in appointments:
            time_diff = abs((appt.scheduled_start - slot_time).total_seconds() / 60)
            if time_diff <= nearby_window.total_seconds() / 60:
                nearby_types.append(appt.appointment_type)

        # Count matches
        matches = sum(1 for t in nearby_types if t == appointment_type)
        total_nearby = len(nearby_types)

        if total_nearby == 0:
            return 0.0, []

        # Higher bonus for more type clustering
        bonus = (matches / max(1, total_nearby)) * 100
        return bonus, nearby_types

    def _calculate_energy_bonus(
        self,
        slot_time: datetime,
        appointment_type: Optional[str],
    ) -> float:
        """Calculate bonus based on doctor energy levels."""
        hour = slot_time.hour

        # Morning (9-12): High energy, good for complex cases
        # Afternoon (12-15): Moderate energy
        # Evening (15-18): Lower energy, good for routine cases

        if not appointment_type:
            return 50.0  # Neutral

        complex_types = [
            AppointmentType.PROCEDURE.value,
            AppointmentType.NEW_CONSULTATION.value,
            AppointmentType.EMERGENCY.value,
        ]
        routine_types = [
            AppointmentType.FOLLOW_UP.value,
            AppointmentType.TELECONSULTATION.value,
        ]

        if appointment_type in complex_types:
            # Complex cases should be early
            if 9 <= hour < 12:
                return 100.0
            elif 12 <= hour < 15:
                return 60.0
            else:
                return 30.0

        elif appointment_type in routine_types:
            # Routine cases can be later
            if 9 <= hour < 12:
                return 60.0
            elif 12 <= hour < 15:
                return 80.0
            else:
                return 100.0

        return 50.0  # Neutral for unknown types

    def _calculate_working_minutes(self, doctor: Doctor) -> int:
        """Calculate total working minutes per day."""
        start = self.WORKING_HOURS_START
        end = self.WORKING_HOURS_END
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        return end_minutes - start_minutes

    def _identify_gaps(
        self,
        appointments: list[Appointment],
        target_date: date,
        doctor: Doctor,
    ) -> list[dict]:
        """Identify gaps in schedule."""
        if not appointments:
            return []

        gaps = []
        sorted_appts = sorted(appointments, key=lambda a: a.scheduled_start)

        for i in range(len(sorted_appts) - 1):
            current_end = sorted_appts[i].scheduled_start + timedelta(
                minutes=sorted_appts[i].duration_minutes
            )
            next_start = sorted_appts[i + 1].scheduled_start

            gap_minutes = int((next_start - current_end).total_seconds() / 60)

            if gap_minutes > 0:
                is_fillable = gap_minutes >= (doctor.slot_duration or 15)
                gaps.append({
                    "gap_start": current_end,
                    "gap_end": next_start,
                    "duration_minutes": gap_minutes,
                    "is_fillable": is_fillable,
                    "reason": "Gap between appointments",
                    "recommended_action": (
                        f"Schedule {gap_minutes // (doctor.slot_duration or 15)} appointments"
                        if is_fillable
                        else "Consider adjusting slot duration"
                    ),
                })

        return gaps

    def _generate_suggestions(
        self,
        utilization_rate: float,
        gaps: list[dict],
        appointments: list[Appointment],
        doctor: Doctor,
    ) -> list[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if utilization_rate < 50:
            suggestions.append(
                "Low utilization detected. Consider promotional campaigns or expanding services."
            )

        if len(gaps) > 5:
            suggestions.append(
                f"Schedule has {len(gaps)} gaps. Consider consolidating appointments."
            )

        fillable_gaps = [g for g in gaps if g["is_fillable"]]
        if fillable_gaps:
            total_fillable = sum(g["duration_minutes"] for g in fillable_gaps)
            potential_slots = total_fillable // (doctor.slot_duration or 15)
            suggestions.append(
                f"You could fit {potential_slots} more appointments in existing gaps."
            )

        if utilization_rate > 90:
            suggestions.append(
                "High utilization! Consider adding more slots or extending hours."
            )

        # Type clustering suggestion
        type_counts = defaultdict(int)
        for appt in appointments:
            type_counts[appt.appointment_type] += 1

        if len(type_counts) > 3:
            suggestions.append(
                "Consider grouping similar appointment types together for better workflow."
            )

        if not suggestions:
            suggestions.append("Schedule is well-optimized!")

        return suggestions


def get_slot_optimizer_service(db: AsyncSession) -> SlotOptimizerService:
    """Factory function for slot optimizer service."""
    return SlotOptimizerService(db)
