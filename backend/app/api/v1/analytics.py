"""
Analytics & Reports API endpoints.

Provides comprehensive clinic analytics and reporting.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.services.analytics import AnalyticsService, get_analytics_service

router = APIRouter()


class AppointmentStatsModel(BaseModel):
    """Appointment statistics response."""
    total: int
    completed: int
    cancelled: int
    no_show: int
    scheduled: int
    completion_rate: float
    cancellation_rate: float
    no_show_rate: float


class RevenueStatsModel(BaseModel):
    """Revenue statistics response."""
    total_revenue: float
    collected: float
    pending: float
    refunded: float
    collection_rate: float
    average_invoice: float


class DoctorUtilizationModel(BaseModel):
    """Doctor utilization metrics."""
    doctor_id: str
    doctor_name: str
    total_slots: int
    booked_slots: int
    completed_appointments: int
    utilization_rate: float
    average_duration_minutes: float
    revenue_generated: float


class DailyMetricModel(BaseModel):
    """Daily metric data point."""
    date: date
    appointments: int
    revenue: float
    new_patients: int


class PatientDemographicsModel(BaseModel):
    """Patient demographics breakdown."""
    total_patients: int
    new_this_period: int
    gender_breakdown: dict
    age_breakdown: dict
    city_breakdown: dict


class NoShowAnalysisModel(BaseModel):
    """No-show analysis response."""
    total_no_shows: int
    by_day_of_week: dict
    by_hour: dict
    worst_day: Optional[str]
    worst_hour: Optional[int]


class DashboardSummaryModel(BaseModel):
    """Dashboard summary combining key metrics."""
    period: str
    appointments: AppointmentStatsModel
    revenue: RevenueStatsModel
    top_doctors: list[DoctorUtilizationModel]
    daily_trend: list[DailyMetricModel]


def get_date_range(period: str) -> tuple[date, date]:
    """Get date range from period string."""
    today = date.today()

    if period == "today":
        return today, today
    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == "week":
        start = today - timedelta(days=today.weekday())  # Monday
        return start, today
    elif period == "month":
        start = today.replace(day=1)
        return start, today
    elif period == "quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_month, day=1)
        return start, today
    elif period == "year":
        start = today.replace(month=1, day=1)
        return start, today
    else:
        # Default to last 30 days
        return today - timedelta(days=30), today


@router.get("/appointments", response_model=AppointmentStatsModel)
async def get_appointment_stats(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|yesterday|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    doctor_id: Optional[UUID] = None,
):
    """
    Get appointment statistics.

    Period can be: today, yesterday, week, month, quarter, year
    Or specify custom start_date and end_date.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_analytics_service(db)
    stats = await service.get_appointment_stats(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
        doctor_id=doctor_id,
    )

    return AppointmentStatsModel(
        total=stats.total,
        completed=stats.completed,
        cancelled=stats.cancelled,
        no_show=stats.no_show,
        scheduled=stats.scheduled,
        completion_rate=round(stats.completion_rate, 2),
        cancellation_rate=round(stats.cancellation_rate, 2),
        no_show_rate=round(stats.no_show_rate, 2),
    )


@router.get("/revenue", response_model=RevenueStatsModel)
async def get_revenue_stats(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|yesterday|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Get revenue statistics.

    Period can be: today, yesterday, week, month, quarter, year
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_analytics_service(db)
    stats = await service.get_revenue_stats(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
    )

    return RevenueStatsModel(
        total_revenue=float(stats.total_revenue),
        collected=float(stats.collected),
        pending=float(stats.pending),
        refunded=float(stats.refunded),
        collection_rate=round(stats.collection_rate, 2),
        average_invoice=float(stats.average_invoice),
    )


@router.get("/doctors/utilization", response_model=list[DoctorUtilizationModel])
async def get_doctor_utilization(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|yesterday|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Get doctor utilization metrics.

    Shows how effectively each doctor's time is being used.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_analytics_service(db)
    utilizations = await service.get_doctor_utilization(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        DoctorUtilizationModel(
            doctor_id=str(u.doctor_id),
            doctor_name=u.doctor_name,
            total_slots=u.total_slots,
            booked_slots=u.booked_slots,
            completed_appointments=u.completed_appointments,
            utilization_rate=round(u.utilization_rate, 2),
            average_duration_minutes=round(u.average_duration_minutes, 1),
            revenue_generated=float(u.revenue_generated),
        )
        for u in utilizations
    ]


@router.get("/daily", response_model=list[DailyMetricModel])
async def get_daily_metrics(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Get day-by-day metrics for charts.

    Returns appointments, revenue, and new patients per day.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_analytics_service(db)
    metrics = await service.get_daily_metrics(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        DailyMetricModel(
            date=m.date,
            appointments=m.appointments,
            revenue=float(m.revenue),
            new_patients=m.new_patients,
        )
        for m in metrics
    ]


@router.get("/patients/demographics", response_model=PatientDemographicsModel)
async def get_patient_demographics(
    db: DbSession,
    current_user: CurrentUser,
    since: Optional[date] = None,
):
    """
    Get patient demographics breakdown.

    Optionally filter to show only patients registered since a date.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_analytics_service(db)
    demographics = await service.get_patient_demographics(
        clinic_id=clinic_id,
        start_date=since,
    )

    return PatientDemographicsModel(
        total_patients=demographics.total_patients,
        new_this_period=demographics.new_this_period,
        gender_breakdown=demographics.gender_breakdown,
        age_breakdown=demographics.age_breakdown,
        city_breakdown=demographics.city_breakdown,
    )


@router.get("/no-shows", response_model=NoShowAnalysisModel)
async def get_no_show_analysis(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Analyze no-show patterns.

    Identifies when no-shows occur most frequently to help optimize scheduling.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_analytics_service(db)
    analysis = await service.get_no_show_analysis(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
    )

    return NoShowAnalysisModel(**analysis)


@router.get("/dashboard", response_model=DashboardSummaryModel)
async def get_dashboard_summary(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|yesterday|week|month|quarter|year)$"),
):
    """
    Get comprehensive dashboard summary.

    Combines appointment stats, revenue, top doctors, and daily trend.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    start_date, end_date = get_date_range(period)
    service = get_analytics_service(db)

    # Get all metrics in parallel
    appt_stats = await service.get_appointment_stats(clinic_id, start_date, end_date)
    revenue_stats = await service.get_revenue_stats(clinic_id, start_date, end_date)
    doctor_utils = await service.get_doctor_utilization(clinic_id, start_date, end_date)
    daily_metrics = await service.get_daily_metrics(clinic_id, start_date, end_date)

    # Sort doctors by utilization and take top 5
    top_doctors = sorted(doctor_utils, key=lambda d: d.utilization_rate, reverse=True)[:5]

    return DashboardSummaryModel(
        period=period,
        appointments=AppointmentStatsModel(
            total=appt_stats.total,
            completed=appt_stats.completed,
            cancelled=appt_stats.cancelled,
            no_show=appt_stats.no_show,
            scheduled=appt_stats.scheduled,
            completion_rate=round(appt_stats.completion_rate, 2),
            cancellation_rate=round(appt_stats.cancellation_rate, 2),
            no_show_rate=round(appt_stats.no_show_rate, 2),
        ),
        revenue=RevenueStatsModel(
            total_revenue=float(revenue_stats.total_revenue),
            collected=float(revenue_stats.collected),
            pending=float(revenue_stats.pending),
            refunded=float(revenue_stats.refunded),
            collection_rate=round(revenue_stats.collection_rate, 2),
            average_invoice=float(revenue_stats.average_invoice),
        ),
        top_doctors=[
            DoctorUtilizationModel(
                doctor_id=str(d.doctor_id),
                doctor_name=d.doctor_name,
                total_slots=d.total_slots,
                booked_slots=d.booked_slots,
                completed_appointments=d.completed_appointments,
                utilization_rate=round(d.utilization_rate, 2),
                average_duration_minutes=round(d.average_duration_minutes, 1),
                revenue_generated=float(d.revenue_generated),
            )
            for d in top_doctors
        ],
        daily_trend=[
            DailyMetricModel(
                date=m.date,
                appointments=m.appointments,
                revenue=float(m.revenue),
                new_patients=m.new_patients,
            )
            for m in daily_metrics
        ],
    )
