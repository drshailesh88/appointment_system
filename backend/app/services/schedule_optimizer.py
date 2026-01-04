"""
Schedule Optimization Service.

Phase 16c: Proactive Intelligence

Analyzes schedules and provides optimization suggestions.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.procedure import Procedure
from app.schemas.insights import BufferSuggestion, OverbookingRisk, TimeGap

logger = logging.getLogger(__name__)


# Average procedure durations (in minutes)
PROCEDURE_DURATIONS = {
    "Echocardiogram": 30,
    "Stress Echo": 45,
    "ECG": 10,
    "Treadmill Test": 30,
    "Angioplasty (PTCA)": 120,
    "Stent Placement": 90,
    "Coronary Angiography": 60,
    "Pacemaker Implantation": 120,
    "Cataract Surgery": 30,
    "LASIK": 20,
    "Intravitreal Injection": 15,
    "Colonoscopy": 45,
    "Upper GI Endoscopy": 30,
    "ERCP": 60,
    "Total Knee Replacement": 180,
    "Total Hip Replacement": 180,
    "ACL Reconstruction": 120,
    "Fracture Fixation": 90,
}

# Default appointment duration
DEFAULT_APPOINTMENT_DURATION = 15


class ScheduleOptimizer:
    """
    Schedule optimization and gap analysis.

    Features:
    - Find schedule gaps for waitlist patients
    - Suggest buffer time for complex procedures
    - Detect overbooking risks
    - Analyze appointment patterns
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_gaps(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        target_date: date,
        min_gap_minutes: int = 30,
    ) -> list[TimeGap]:
        """
        Find gaps in doctor's schedule.

        Args:
            clinic_id: Clinic ID
            doctor_id: Doctor ID
            target_date: Date to analyze
            min_gap_minutes: Minimum gap size to report

        Returns:
            List of time gaps
        """
        # Get all appointments for the day
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.clinic_id == clinic_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date >= start_datetime,
                    Appointment.appointment_date <= end_datetime,
                    Appointment.status.in_(["scheduled", "confirmed"]),
                )
            )
            .order_by(Appointment.appointment_date)
        )

        result = await self.db.execute(stmt)
        appointments = result.scalars().all()

        if not appointments:
            # No appointments - entire day is available
            # Assume clinic hours: 9 AM - 6 PM
            return [
                TimeGap(
                    start_time=datetime.combine(target_date, datetime.min.time().replace(hour=9)),
                    end_time=datetime.combine(target_date, datetime.min.time().replace(hour=18)),
                    duration_minutes=540,  # 9 hours
                    doctor_id=doctor_id,
                    doctor_name="",  # Would fetch doctor name
                )
            ]

        # Find gaps between appointments
        gaps = []
        clinic_start = datetime.combine(target_date, datetime.min.time().replace(hour=9))
        clinic_end = datetime.combine(target_date, datetime.min.time().replace(hour=18))

        # Check gap before first appointment
        first_appt = appointments[0]
        if (first_appt.appointment_date - clinic_start).total_seconds() / 60 >= min_gap_minutes:
            gaps.append(
                TimeGap(
                    start_time=clinic_start,
                    end_time=first_appt.appointment_date,
                    duration_minutes=int((first_appt.appointment_date - clinic_start).total_seconds() / 60),
                    doctor_id=doctor_id,
                    doctor_name="",
                )
            )

        # Check gaps between appointments
        for i in range(len(appointments) - 1):
            current_appt = appointments[i]
            next_appt = appointments[i + 1]

            # Estimate end time of current appointment
            duration = current_appt.duration_minutes or DEFAULT_APPOINTMENT_DURATION
            current_end = current_appt.appointment_date + timedelta(minutes=duration)

            # Calculate gap
            gap_minutes = (next_appt.appointment_date - current_end).total_seconds() / 60

            if gap_minutes >= min_gap_minutes:
                gaps.append(
                    TimeGap(
                        start_time=current_end,
                        end_time=next_appt.appointment_date,
                        duration_minutes=int(gap_minutes),
                        doctor_id=doctor_id,
                        doctor_name="",
                    )
                )

        # Check gap after last appointment
        last_appt = appointments[-1]
        last_duration = last_appt.duration_minutes or DEFAULT_APPOINTMENT_DURATION
        last_end = last_appt.appointment_date + timedelta(minutes=last_duration)

        if (clinic_end - last_end).total_seconds() / 60 >= min_gap_minutes:
            gaps.append(
                TimeGap(
                    start_time=last_end,
                    end_time=clinic_end,
                    duration_minutes=int((clinic_end - last_end).total_seconds() / 60),
                    doctor_id=doctor_id,
                    doctor_name="",
                )
            )

        return gaps

    async def suggest_buffer_time(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        procedure_type: Optional[str] = None,
    ) -> Optional[BufferSuggestion]:
        """
        Suggest buffer time for a patient based on history.

        Args:
            patient_id: Patient ID
            doctor_id: Doctor ID
            procedure_type: Optional procedure type

        Returns:
            Buffer suggestion or None
        """
        # Get patient's appointment history
        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.status == "completed",
                )
            )
            .order_by(Appointment.appointment_date.desc())
            .limit(10)
        )

        result = await self.db.execute(stmt)
        appointments = result.scalars().all()

        if not appointments:
            return None

        # Calculate average overrun
        overruns = []
        for appt in appointments:
            if appt.duration_minutes and appt.actual_duration_minutes:
                overrun = appt.actual_duration_minutes - appt.duration_minutes
                if overrun > 0:
                    overruns.append(overrun)

        if not overruns:
            return None

        avg_overrun = sum(overruns) / len(overruns)

        # Only suggest if significant overrun (> 5 minutes)
        if avg_overrun > 5:
            return BufferSuggestion(
                suggested_duration_minutes=int(avg_overrun),
                reason=f"Patient's appointments typically run {int(avg_overrun)} minutes over schedule",
                confidence=min(1.0, len(overruns) / 5),  # More data = higher confidence
            )

        return None

    async def analyze_overbooking_risk(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        target_date: date,
    ) -> OverbookingRisk:
        """
        Analyze if a day is overbooked based on procedure mix.

        Args:
            clinic_id: Clinic ID
            doctor_id: Doctor ID
            target_date: Date to analyze

        Returns:
            Overbooking risk assessment
        """
        # Get appointments and procedures for the day
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        # Get appointments
        appt_stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.clinic_id == clinic_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date >= start_datetime,
                    Appointment.appointment_date <= end_datetime,
                    Appointment.status.in_(["scheduled", "confirmed"]),
                )
            )
        )

        result = await self.db.execute(appt_stmt)
        appointments = result.scalars().all()

        # Get procedures scheduled for the day
        proc_stmt = (
            select(Procedure)
            .where(
                and_(
                    Procedure.clinic_id == clinic_id,
                    Procedure.doctor_id == doctor_id,
                    func.date(Procedure.performed_at) == target_date,
                )
            )
        )

        proc_result = await self.db.execute(proc_stmt)
        procedures = proc_result.scalars().all()

        # Calculate total estimated duration
        total_minutes = 0

        for appt in appointments:
            duration = appt.duration_minutes or DEFAULT_APPOINTMENT_DURATION
            total_minutes += duration

        for proc in procedures:
            # Estimate based on procedure type
            duration = PROCEDURE_DURATIONS.get(
                proc.procedure_type,
                60,  # Default for unknown procedures
            )
            total_minutes += duration

        # Assume 9-hour workday (540 minutes)
        available_minutes = 540
        utilization = (total_minutes / available_minutes) * 100

        # Determine risk level
        if utilization < 80:
            risk_level = "low"
            recommendations = [
                f"Good schedule - {int(available_minutes - total_minutes)} minutes available",
                "Consider filling gaps with waitlist patients",
            ]
        elif utilization < 100:
            risk_level = "medium"
            recommendations = [
                "Schedule is full but manageable",
                "Avoid adding complex procedures",
            ]
        else:
            risk_level = "high"
            recommendations = [
                f"OVERBOOKED: {int(total_minutes - available_minutes)} minutes over capacity",
                "Reschedule non-urgent appointments",
                "Add buffer time between procedures",
            ]

        return OverbookingRisk(
            risk_level=risk_level,
            total_procedures=len(appointments) + len(procedures),
            estimated_duration_minutes=total_minutes,
            available_minutes=available_minutes,
            recommendations=recommendations,
        )

    async def get_optimal_slot_for_procedure(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        procedure_type: str,
        target_date: date,
    ) -> Optional[datetime]:
        """
        Find optimal slot for a procedure type.

        Args:
            clinic_id: Clinic ID
            doctor_id: Doctor ID
            procedure_type: Type of procedure
            target_date: Preferred date

        Returns:
            Optimal datetime slot or None
        """
        # Get procedure duration
        required_minutes = PROCEDURE_DURATIONS.get(procedure_type, 60)

        # Find gaps
        gaps = await self.find_gaps(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            target_date=target_date,
            min_gap_minutes=required_minutes,
        )

        if not gaps:
            return None

        # Return first suitable gap
        return gaps[0].start_time

    async def get_patient_appointment_patterns(
        self,
        patient_id: UUID,
    ) -> dict:
        """
        Analyze patient's appointment patterns.

        Args:
            patient_id: Patient ID

        Returns:
            Pattern analysis
        """
        # Get patient's appointments
        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_date.desc())
            .limit(20)
        )

        result = await self.db.execute(stmt)
        appointments = result.scalars().all()

        if not appointments:
            return {
                "total_appointments": 0,
                "no_show_rate": 0,
                "cancellation_rate": 0,
                "avg_delay_minutes": 0,
            }

        total = len(appointments)
        no_shows = sum(1 for a in appointments if a.status == "no_show")
        cancellations = sum(1 for a in appointments if a.status == "cancelled")

        return {
            "total_appointments": total,
            "no_show_rate": (no_shows / total) * 100 if total > 0 else 0,
            "cancellation_rate": (cancellations / total) * 100 if total > 0 else 0,
            "avg_delay_minutes": 0,  # Would calculate from check-in times
            "reliability_score": ((total - no_shows - cancellations) / total) * 100 if total > 0 else 0,
        }
