"""
Smart Scheduling Service.

AI-powered scheduling suggestions based on historical patterns,
doctor availability, and patient preferences.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import UUID
from collections import Counter, defaultdict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.doctor import Doctor
from app.models.patient import Patient

logger = logging.getLogger(__name__)


@dataclass
class SlotSuggestion:
    """A suggested appointment slot with scoring."""
    slot_time: datetime
    score: float  # 0-100 score indicating how optimal this slot is
    reasons: list[str]  # Human-readable reasons for this suggestion
    doctor_id: UUID
    duration_minutes: int


@dataclass
class SchedulingPattern:
    """Scheduling patterns for analysis."""
    peak_hours: dict[int, int]  # hour -> count
    peak_days: dict[int, int]  # weekday -> count (0=Monday)
    average_duration: float
    preferred_times: list[time]  # Most common appointment times
    follow_up_interval_days: int | None  # Average days between follow-ups


@dataclass
class DoctorAvailabilityScore:
    """Doctor availability and preference scoring."""
    doctor_id: UUID
    available_slots: int
    current_bookings: int
    utilization_rate: float
    preferred_slot_duration: int


class SmartSchedulingService:
    """
    AI-powered smart scheduling service.

    Analyzes historical patterns to suggest optimal appointment times
    based on patient history, doctor availability, and booking density.
    """

    def __init__(self, db: AsyncSession):
        """Initialize smart scheduling service."""
        self.db = db

    async def get_slot_suggestions(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        appointment_type: AppointmentType,
        preferred_date: Optional[date] = None,
        duration_minutes: int = 15,
        max_suggestions: int = 5,
    ) -> list[SlotSuggestion]:
        """
        Get smart slot suggestions for a patient.

        Args:
            patient_id: Patient to book for
            doctor_id: Doctor to see
            appointment_type: Type of appointment
            preferred_date: Optional preferred date (defaults to next 7 days)
            duration_minutes: Required duration
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggested slots ranked by score
        """
        # Get patient patterns
        patient_patterns = await self._analyze_patient_patterns(patient_id, doctor_id)

        # Get doctor patterns and availability
        doctor_patterns = await self._analyze_doctor_patterns(doctor_id)

        # Get current booking density
        booking_density = await self._get_booking_density(
            doctor_id,
            preferred_date or date.today(),
        )

        # Generate candidate slots
        candidates = await self._generate_candidate_slots(
            doctor_id,
            preferred_date or date.today(),
            duration_minutes,
            days_ahead=7,
        )

        # Score each candidate
        suggestions = []
        for slot in candidates:
            score, reasons = self._score_slot(
                slot,
                patient_patterns,
                doctor_patterns,
                booking_density,
                appointment_type,
            )

            suggestions.append(SlotSuggestion(
                slot_time=slot,
                score=score,
                reasons=reasons,
                doctor_id=doctor_id,
                duration_minutes=duration_minutes,
            ))

        # Sort by score and return top N
        suggestions.sort(key=lambda x: x.score, reverse=True)
        return suggestions[:max_suggestions]

    async def _analyze_patient_patterns(
        self,
        patient_id: UUID,
        doctor_id: UUID,
    ) -> SchedulingPattern:
        """Analyze patient's historical appointment patterns."""
        # Get patient's past appointments with this doctor
        result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.status.in_([
                        AppointmentStatus.COMPLETED.value,
                        AppointmentStatus.SCHEDULED.value,
                    ]),
                )
            ).order_by(Appointment.scheduled_start.desc()).limit(20)
        )
        appointments = result.scalars().all()

        if not appointments:
            # No history - return empty pattern
            return SchedulingPattern(
                peak_hours={},
                peak_days={},
                average_duration=15.0,
                preferred_times=[],
                follow_up_interval_days=None,
            )

        # Analyze hour preferences
        hour_counts = Counter(appt.scheduled_start.hour for appt in appointments)

        # Analyze day preferences
        day_counts = Counter(appt.scheduled_start.weekday() for appt in appointments)

        # Calculate average duration
        avg_duration = sum(appt.duration_minutes for appt in appointments) / len(appointments)

        # Find preferred times (most common appointment times)
        time_counts = Counter(
            appt.scheduled_start.time().replace(second=0, microsecond=0)
            for appt in appointments
        )
        preferred_times = [t for t, _ in time_counts.most_common(3)]

        # Calculate follow-up interval for follow-up appointments
        follow_up_interval = None
        if len(appointments) >= 2:
            intervals = []
            for i in range(len(appointments) - 1):
                delta = appointments[i].scheduled_start - appointments[i + 1].scheduled_start
                intervals.append(abs(delta.days))
            if intervals:
                follow_up_interval = sum(intervals) // len(intervals)

        return SchedulingPattern(
            peak_hours=dict(hour_counts),
            peak_days=dict(day_counts),
            average_duration=avg_duration,
            preferred_times=preferred_times,
            follow_up_interval_days=follow_up_interval,
        )

    async def _analyze_doctor_patterns(self, doctor_id: UUID) -> dict:
        """Analyze doctor's scheduling patterns and preferences."""
        # Get doctor
        result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = result.scalar_one_or_none()

        if not doctor:
            return {
                "working_hours": {},
                "slot_duration": 15,
                "busy_hours": {},
                "typical_load": {},
            }

        # Get recent appointments to find busy patterns
        thirty_days_ago = datetime.now() - timedelta(days=30)
        appt_result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.scheduled_start >= thirty_days_ago,
                    Appointment.status != AppointmentStatus.CANCELLED.value,
                )
            )
        )
        appointments = appt_result.scalars().all()

        # Analyze busy hours
        hour_counts = Counter(appt.scheduled_start.hour for appt in appointments)
        day_counts = Counter(appt.scheduled_start.weekday() for appt in appointments)

        return {
            "working_hours": doctor.working_hours or {},
            "slot_duration": doctor.slot_duration,
            "busy_hours": dict(hour_counts),
            "typical_load": dict(day_counts),
        }

    async def _get_booking_density(
        self,
        doctor_id: UUID,
        start_date: date,
        days_ahead: int = 7,
    ) -> dict[date, int]:
        """Get booking density for upcoming days."""
        end_date = start_date + timedelta(days=days_ahead)
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        # Count appointments per day
        result = await self.db.execute(
            select(
                func.date(Appointment.scheduled_start).label("appt_date"),
                func.count().label("count"),
            ).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.scheduled_start >= start_dt,
                    Appointment.scheduled_start <= end_dt,
                    Appointment.status != AppointmentStatus.CANCELLED.value,
                )
            ).group_by(func.date(Appointment.scheduled_start))
        )

        density = {}
        for row in result.all():
            density[row.appt_date] = row.count

        return density

    async def _generate_candidate_slots(
        self,
        doctor_id: UUID,
        start_date: date,
        duration_minutes: int,
        days_ahead: int = 7,
    ) -> list[datetime]:
        """Generate candidate time slots for scheduling."""
        # Get doctor's working hours
        result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = result.scalar_one_or_none()

        if not doctor or not doctor.working_hours:
            # Default working hours if not set
            working_hours = {
                "monday": [{"start": "09:00", "end": "17:00"}],
                "tuesday": [{"start": "09:00", "end": "17:00"}],
                "wednesday": [{"start": "09:00", "end": "17:00"}],
                "thursday": [{"start": "09:00", "end": "17:00"}],
                "friday": [{"start": "09:00", "end": "17:00"}],
                "saturday": [{"start": "09:00", "end": "13:00"}],
            }
            slot_duration = 15
        else:
            working_hours = doctor.working_hours
            slot_duration = doctor.slot_duration

        # Get existing appointments to exclude booked slots
        end_date = start_date + timedelta(days=days_ahead)
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        appt_result = await self.db.execute(
            select(Appointment.scheduled_start, Appointment.scheduled_end).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.scheduled_start >= start_dt,
                    Appointment.scheduled_start <= end_dt,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED.value,
                        AppointmentStatus.CONFIRMED.value,
                    ]),
                )
            )
        )
        booked_slots = [
            (row.scheduled_start, row.scheduled_end)
            for row in appt_result.all()
        ]

        # Generate candidate slots
        candidates = []
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        current_date = start_date

        while current_date <= end_date:
            if current_date < date.today():
                current_date += timedelta(days=1)
                continue

            day_name = day_names[current_date.weekday()]
            day_schedule = working_hours.get(day_name)

            if not day_schedule:
                current_date += timedelta(days=1)
                continue

            # For each working period in the day
            for period in day_schedule:
                start_time = datetime.strptime(period["start"], "%H:%M").time()
                end_time = datetime.strptime(period["end"], "%H:%M").time()

                # Generate slots
                current_slot = datetime.combine(current_date, start_time)
                period_end = datetime.combine(current_date, end_time)

                while current_slot + timedelta(minutes=duration_minutes) <= period_end:
                    slot_end = current_slot + timedelta(minutes=duration_minutes)

                    # Check if slot is available
                    is_booked = any(
                        (current_slot < end and slot_end > start)
                        for start, end in booked_slots
                    )

                    if not is_booked and current_slot > datetime.now():
                        candidates.append(current_slot)

                    current_slot += timedelta(minutes=slot_duration)

            current_date += timedelta(days=1)

        return candidates

    def _score_slot(
        self,
        slot: datetime,
        patient_patterns: SchedulingPattern,
        doctor_patterns: dict,
        booking_density: dict[date, int],
        appointment_type: AppointmentType,
    ) -> tuple[float, list[str]]:
        """
        Score a candidate slot based on multiple factors.

        Returns:
            Tuple of (score, reasons) where score is 0-100
        """
        score = 50.0  # Base score
        reasons = []

        # Factor 1: Patient's historical preferences (20 points)
        slot_hour = slot.hour
        slot_day = slot.weekday()

        if slot_hour in patient_patterns.peak_hours:
            frequency = patient_patterns.peak_hours[slot_hour]
            score += min(10, frequency * 2)
            reasons.append(f"Patient previously booked at {slot_hour}:00")

        if slot_day in patient_patterns.peak_days:
            frequency = patient_patterns.peak_days[slot_day]
            score += min(10, frequency * 2)
            day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][slot_day]
            reasons.append(f"Patient prefers {day_name}s")

        # Factor 2: Match patient's preferred times (15 points)
        slot_time = slot.time().replace(second=0, microsecond=0)
        if slot_time in patient_patterns.preferred_times:
            score += 15
            reasons.append(f"Matches patient's usual time ({slot_time.strftime('%H:%M')})")

        # Factor 3: Booking density (15 points)
        # Prefer days with lower booking density
        slot_date = slot.date()
        density = booking_density.get(slot_date, 0)
        max_density = max(booking_density.values()) if booking_density else 10

        if max_density > 0:
            density_score = 15 * (1 - (density / max_density))
            score += density_score
            if density < 5:
                reasons.append("Light booking day - shorter wait expected")

        # Factor 4: Doctor's busy hours (10 points)
        # Prefer times when doctor is less busy
        doctor_busy = doctor_patterns.get("busy_hours", {})
        if doctor_busy:
            max_busy = max(doctor_busy.values())
            hour_busy = doctor_busy.get(slot_hour, 0)
            if max_busy > 0:
                score += 10 * (1 - (hour_busy / max_busy))
                if hour_busy < max_busy / 2:
                    reasons.append("Doctor typically less busy at this time")

        # Factor 5: Time of day preferences (10 points)
        # Morning slots (9-11 AM) often preferred
        if 9 <= slot_hour <= 11:
            score += 10
            reasons.append("Optimal morning time slot")
        # Evening slots for working patients
        elif 17 <= slot_hour <= 19:
            score += 8
            reasons.append("Convenient evening slot")

        # Factor 6: Follow-up interval matching (10 points)
        if appointment_type == AppointmentType.FOLLOW_UP and patient_patterns.follow_up_interval_days:
            # This would require checking last appointment date
            # For now, add slight bonus for follow-ups
            score += 5
            reasons.append("Appropriate timing for follow-up")

        # Factor 7: Proximity (10 points)
        # Prefer slots in the next 2-3 days for urgent, but not same day (too rushed)
        days_ahead = (slot.date() - date.today()).days
        if 1 <= days_ahead <= 3:
            score += 10
            reasons.append("Available soon")
        elif days_ahead == 0:
            score += 5
            reasons.append("Same-day availability")

        # Factor 8: Avoid late afternoon slots near closing (penalize)
        if slot_hour >= 18:
            score -= 5
            # Don't add reason for penalties

        # Factor 9: Weekend availability (bonus for convenience)
        if slot_day >= 5:  # Saturday or Sunday
            score += 5
            reasons.append("Weekend availability")

        # Ensure score is in 0-100 range
        score = max(0, min(100, score))

        # Limit reasons to top 3
        if len(reasons) > 3:
            reasons = reasons[:3]

        return score, reasons

    async def get_optimal_booking_windows(
        self,
        doctor_id: UUID,
        date_range_days: int = 30,
    ) -> dict:
        """
        Get optimal booking windows for a doctor.

        Analyzes patterns to suggest best times for appointments.

        Args:
            doctor_id: Doctor to analyze
            date_range_days: Days of history to analyze

        Returns:
            Dictionary with optimal windows and patterns
        """
        # Analyze past appointments
        start_date = datetime.now() - timedelta(days=date_range_days)

        result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.scheduled_start >= start_date,
                    Appointment.status == AppointmentStatus.COMPLETED.value,
                )
            )
        )
        appointments = result.scalars().all()

        # Analyze by hour
        hourly_stats = defaultdict(lambda: {"count": 0, "avg_wait": 0, "total_wait": 0})

        for appt in appointments:
            hour = appt.scheduled_start.hour
            hourly_stats[hour]["count"] += 1
            if appt.wait_time_minutes:
                hourly_stats[hour]["total_wait"] += appt.wait_time_minutes

        # Calculate averages
        optimal_windows = []
        for hour in range(24):
            if hour in hourly_stats and hourly_stats[hour]["count"] > 0:
                stats = hourly_stats[hour]
                avg_wait = stats["total_wait"] / stats["count"] if stats["count"] > 0 else 0

                optimal_windows.append({
                    "hour": hour,
                    "time_range": f"{hour:02d}:00 - {hour+1:02d}:00",
                    "appointment_count": stats["count"],
                    "average_wait_minutes": round(avg_wait, 1),
                    "is_optimal": avg_wait < 15 and stats["count"] >= 5,
                })

        return {
            "doctor_id": str(doctor_id),
            "analyzed_period_days": date_range_days,
            "optimal_windows": optimal_windows,
            "total_appointments_analyzed": len(appointments),
        }

    async def get_pattern_analysis(
        self,
        doctor_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Get detailed pattern analysis for a doctor.

        Returns insights about booking patterns, peak times, etc.
        """
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.scheduled_start >= start_dt,
                    Appointment.scheduled_start <= end_dt,
                )
            )
        )
        appointments = result.scalars().all()

        if not appointments:
            return {
                "doctor_id": str(doctor_id),
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_appointments": 0,
                "patterns": {},
            }

        # Analyze patterns
        hour_counts = Counter(appt.scheduled_start.hour for appt in appointments)
        day_counts = Counter(appt.scheduled_start.weekday() for appt in appointments)
        type_counts = Counter(appt.appointment_type for appt in appointments)

        # Find peak hour
        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 9
        peak_day = max(day_counts, key=day_counts.get) if day_counts else 0

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        return {
            "doctor_id": str(doctor_id),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_appointments": len(appointments),
            "patterns": {
                "peak_hour": peak_hour,
                "peak_hour_range": f"{peak_hour:02d}:00 - {peak_hour+1:02d}:00",
                "peak_day": day_names[peak_day],
                "busiest_day_count": day_counts[peak_day],
                "hourly_distribution": dict(hour_counts),
                "daily_distribution": {
                    day_names[i]: day_counts.get(i, 0)
                    for i in range(7)
                },
                "appointment_types": dict(type_counts),
            },
            "recommendations": self._generate_recommendations(
                hour_counts,
                day_counts,
                appointments,
            ),
        }

    def _generate_recommendations(
        self,
        hour_counts: Counter,
        day_counts: Counter,
        appointments: list[Appointment],
    ) -> list[str]:
        """Generate scheduling recommendations based on patterns."""
        recommendations = []

        # Check for overbooked hours
        if hour_counts:
            max_hour_count = max(hour_counts.values())
            avg_hour_count = sum(hour_counts.values()) / len(hour_counts)

            if max_hour_count > avg_hour_count * 1.5:
                peak_hour = max(hour_counts, key=hour_counts.get)
                recommendations.append(
                    f"Consider distributing appointments more evenly - {peak_hour:02d}:00 hour is heavily booked"
                )

        # Check for underutilized days
        if day_counts:
            max_day_count = max(day_counts.values())
            min_day_count = min(day_counts.values())

            if max_day_count > min_day_count * 2:
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                min_day = min(day_counts, key=day_counts.get)
                recommendations.append(
                    f"{day_names[min_day]}s are underutilized - consider promotions or extended hours"
                )

        # Check average duration
        completed = [a for a in appointments if a.consultation_duration_minutes]
        if completed:
            avg_duration = sum(a.consultation_duration_minutes for a in completed) / len(completed)
            if avg_duration > 20:
                recommendations.append(
                    f"Average consultation takes {avg_duration:.0f} minutes - consider longer slot durations"
                )

        return recommendations


def get_smart_scheduling_service(db: AsyncSession) -> SmartSchedulingService:
    """Factory function for smart scheduling service."""
    return SmartSchedulingService(db)
