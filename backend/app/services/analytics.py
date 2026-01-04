"""
Analytics & Reports Service.

Provides comprehensive analytics for clinic operations:
- Appointment statistics (daily, weekly, monthly)
- Doctor utilization metrics
- Revenue tracking
- No-show analysis
- Patient demographics
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.invoice import Invoice
from app.models.payment import Payment

logger = logging.getLogger(__name__)


@dataclass
class AppointmentStats:
    """Appointment statistics for a time period."""
    total: int
    completed: int
    cancelled: int
    no_show: int
    scheduled: int
    completion_rate: float
    cancellation_rate: float
    no_show_rate: float


@dataclass
class RevenueStats:
    """Revenue statistics for a time period."""
    total_revenue: Decimal
    collected: Decimal
    pending: Decimal
    refunded: Decimal
    collection_rate: float
    average_invoice: Decimal


@dataclass
class DoctorUtilization:
    """Doctor utilization metrics."""
    doctor_id: UUID
    doctor_name: str
    total_slots: int
    booked_slots: int
    completed_appointments: int
    utilization_rate: float
    average_duration_minutes: float
    revenue_generated: Decimal


@dataclass
class DailyMetric:
    """A single day's metrics."""
    date: date
    appointments: int
    revenue: Decimal
    new_patients: int


@dataclass
class PatientDemographics:
    """Patient demographic breakdown."""
    total_patients: int
    new_this_period: int
    gender_breakdown: dict
    age_breakdown: dict
    city_breakdown: dict


class AnalyticsService:
    """
    Analytics and reporting service.

    Provides metrics and insights for clinic operations.
    """

    def __init__(self, db: AsyncSession):
        """Initialize analytics service with database session."""
        self.db = db

    async def get_appointment_stats(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        doctor_id: Optional[UUID] = None,
    ) -> AppointmentStats:
        """
        Get appointment statistics for a time period.

        Args:
            clinic_id: Clinic to analyze
            start_date: Period start
            end_date: Period end
            doctor_id: Optional doctor filter
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Build base query
        base_filter = and_(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_start >= start_dt,
            Appointment.scheduled_start <= end_dt,
        )

        if doctor_id:
            base_filter = and_(base_filter, Appointment.doctor_id == doctor_id)

        # Count by status
        result = await self.db.execute(
            select(
                func.count().label("total"),
                func.sum(case((Appointment.status == AppointmentStatus.COMPLETED.value, 1), else_=0)).label("completed"),
                func.sum(case((Appointment.status == AppointmentStatus.CANCELLED.value, 1), else_=0)).label("cancelled"),
                func.sum(case((Appointment.status == AppointmentStatus.NO_SHOW.value, 1), else_=0)).label("no_show"),
                func.sum(case((Appointment.status == AppointmentStatus.SCHEDULED.value, 1), else_=0)).label("scheduled"),
            ).where(base_filter)
        )
        row = result.one()

        total = row.total or 0
        completed = row.completed or 0
        cancelled = row.cancelled or 0
        no_show = row.no_show or 0
        scheduled = row.scheduled or 0

        return AppointmentStats(
            total=total,
            completed=completed,
            cancelled=cancelled,
            no_show=no_show,
            scheduled=scheduled,
            completion_rate=(completed / total * 100) if total > 0 else 0.0,
            cancellation_rate=(cancelled / total * 100) if total > 0 else 0.0,
            no_show_rate=(no_show / total * 100) if total > 0 else 0.0,
        )

    async def get_revenue_stats(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        doctor_id: Optional[UUID] = None,
    ) -> RevenueStats:
        """
        Get revenue statistics for a time period.

        Args:
            clinic_id: Clinic to analyze
            start_date: Period start
            end_date: Period end
            doctor_id: Optional doctor filter
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Query invoices
        invoice_filter = and_(
            Invoice.clinic_id == clinic_id,
            Invoice.created_at >= start_dt,
            Invoice.created_at <= end_dt,
        )

        result = await self.db.execute(
            select(
                func.count().label("count"),
                func.coalesce(func.sum(Invoice.total_amount), 0).label("total"),
                func.coalesce(func.sum(Invoice.paid_amount), 0).label("paid"),
            ).where(invoice_filter)
        )
        row = result.one()

        count = row.count or 0
        total = Decimal(str(row.total or 0))
        paid = Decimal(str(row.paid or 0))
        pending = total - paid

        return RevenueStats(
            total_revenue=total,
            collected=paid,
            pending=pending,
            refunded=Decimal("0"),  # Would need refund tracking
            collection_rate=(float(paid) / float(total) * 100) if total > 0 else 0.0,
            average_invoice=(total / count) if count > 0 else Decimal("0"),
        )

    async def get_doctor_utilization(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[DoctorUtilization]:
        """
        Get utilization metrics for all doctors.

        Args:
            clinic_id: Clinic to analyze
            start_date: Period start
            end_date: Period end
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Get doctors
        doctors_result = await self.db.execute(
            select(Doctor).where(Doctor.clinic_id == clinic_id)
        )
        doctors = doctors_result.scalars().all()

        utilizations = []
        for doctor in doctors:
            # Count appointments
            appt_result = await self.db.execute(
                select(
                    func.count().label("total"),
                    func.sum(case((Appointment.status == AppointmentStatus.COMPLETED.value, 1), else_=0)).label("completed"),
                    func.avg(Appointment.duration_minutes).label("avg_duration"),
                ).where(
                    and_(
                        Appointment.doctor_id == doctor.id,
                        Appointment.scheduled_start >= start_dt,
                        Appointment.scheduled_start <= end_dt,
                    )
                )
            )
            appt_row = appt_result.one()

            # Calculate available slots (rough estimate based on working hours)
            days_in_period = (end_date - start_date).days + 1
            slots_per_day = 8 * 60 // (doctor.slot_duration or 15)  # 8 hour day
            total_slots = slots_per_day * days_in_period

            booked = appt_row.total or 0
            completed = appt_row.completed or 0

            utilizations.append(DoctorUtilization(
                doctor_id=doctor.id,
                doctor_name=doctor.name,
                total_slots=total_slots,
                booked_slots=booked,
                completed_appointments=completed,
                utilization_rate=(booked / total_slots * 100) if total_slots > 0 else 0.0,
                average_duration_minutes=float(appt_row.avg_duration or doctor.slot_duration or 15),
                revenue_generated=Decimal("0"),  # Would calculate from invoices
            ))

        return utilizations

    async def get_daily_metrics(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[DailyMetric]:
        """
        Get day-by-day metrics for charts.

        Args:
            clinic_id: Clinic to analyze
            start_date: Period start
            end_date: Period end
        """
        metrics = []
        current = start_date

        while current <= end_date:
            next_day = current + timedelta(days=1)
            current_dt = datetime.combine(current, datetime.min.time())
            next_dt = datetime.combine(next_day, datetime.min.time())

            # Appointments for this day
            appt_result = await self.db.execute(
                select(func.count()).where(
                    and_(
                        Appointment.clinic_id == clinic_id,
                        Appointment.scheduled_start >= current_dt,
                        Appointment.scheduled_start < next_dt,
                    )
                )
            )
            appointments = appt_result.scalar() or 0

            # Revenue for this day
            revenue_result = await self.db.execute(
                select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                    and_(
                        Invoice.clinic_id == clinic_id,
                        Invoice.created_at >= current_dt,
                        Invoice.created_at < next_dt,
                    )
                )
            )
            revenue = Decimal(str(revenue_result.scalar() or 0))

            # New patients registered this day
            patients_result = await self.db.execute(
                select(func.count()).where(
                    and_(
                        Patient.clinic_id == clinic_id,
                        Patient.created_at >= current_dt,
                        Patient.created_at < next_dt,
                    )
                )
            )
            new_patients = patients_result.scalar() or 0

            metrics.append(DailyMetric(
                date=current,
                appointments=appointments,
                revenue=revenue,
                new_patients=new_patients,
            ))

            current = next_day

        return metrics

    async def get_patient_demographics(
        self,
        clinic_id: UUID,
        start_date: Optional[date] = None,
    ) -> PatientDemographics:
        """
        Get patient demographic breakdown.

        Args:
            clinic_id: Clinic to analyze
            start_date: Only count patients registered after this date
        """
        # Total patients
        total_result = await self.db.execute(
            select(func.count()).where(Patient.clinic_id == clinic_id)
        )
        total = total_result.scalar() or 0

        # New this period
        new_count = 0
        if start_date:
            start_dt = datetime.combine(start_date, datetime.min.time())
            new_result = await self.db.execute(
                select(func.count()).where(
                    and_(
                        Patient.clinic_id == clinic_id,
                        Patient.created_at >= start_dt,
                    )
                )
            )
            new_count = new_result.scalar() or 0

        # Gender breakdown
        gender_result = await self.db.execute(
            select(
                Patient.gender,
                func.count().label("count"),
            ).where(Patient.clinic_id == clinic_id)
            .group_by(Patient.gender)
        )
        gender_breakdown = {
            row.gender or "unknown": row.count
            for row in gender_result.all()
        }

        # City breakdown
        city_result = await self.db.execute(
            select(
                Patient.city,
                func.count().label("count"),
            ).where(Patient.clinic_id == clinic_id)
            .group_by(Patient.city)
        )
        city_breakdown = {
            row.city or "unknown": row.count
            for row in city_result.all()
        }

        return PatientDemographics(
            total_patients=total,
            new_this_period=new_count,
            gender_breakdown=gender_breakdown,
            age_breakdown={},  # Would need date_of_birth calculation
            city_breakdown=city_breakdown,
        )

    async def get_no_show_analysis(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Analyze no-show patterns.

        Returns insights about when no-shows occur most frequently.
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Get no-show appointments
        result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.clinic_id == clinic_id,
                    Appointment.status == AppointmentStatus.NO_SHOW.value,
                    Appointment.scheduled_start >= start_dt,
                    Appointment.scheduled_start <= end_dt,
                )
            )
        )
        no_shows = result.scalars().all()

        # Analyze by day of week
        day_counts = {i: 0 for i in range(7)}  # 0=Monday, 6=Sunday
        hour_counts = {i: 0 for i in range(24)}

        for appt in no_shows:
            day_counts[appt.scheduled_start.weekday()] += 1
            hour_counts[appt.scheduled_start.hour] += 1

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_day = {day_names[i]: count for i, count in day_counts.items()}

        return {
            "total_no_shows": len(no_shows),
            "by_day_of_week": by_day,
            "by_hour": hour_counts,
            "worst_day": max(by_day, key=by_day.get) if by_day else None,
            "worst_hour": max(hour_counts, key=hour_counts.get) if hour_counts else None,
        }


def get_analytics_service(db: AsyncSession) -> AnalyticsService:
    """Factory function for analytics service."""
    return AnalyticsService(db)
