"""
Reports & Exports API endpoints.

Phase 8: Downloadable PDF and Excel reports.
"""

from datetime import date, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.api.deps import CurrentUser, DbSession
from app.services.reports import ReportService, get_report_service

router = APIRouter()


class ReportFormat(str, Enum):
    """Supported report formats."""
    PDF = "pdf"
    EXCEL = "excel"


class ReportType(str, Enum):
    """Available report types."""
    DAILY_SUMMARY = "daily_summary"
    MONTHLY_ANALYTICS = "monthly_analytics"
    REVENUE = "revenue"
    APPOINTMENTS = "appointments"
    DOCTOR_UTILIZATION = "doctor_utilization"
    PATIENT_DEMOGRAPHICS = "patient_demographics"


def get_date_range(period: str) -> tuple[date, date]:
    """Get date range from period string."""
    today = date.today()

    if period == "today":
        return today, today
    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == "week":
        start = today - timedelta(days=today.weekday())
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
        return today - timedelta(days=30), today


# ========== PDF Report Endpoints ==========

@router.get("/daily-summary/pdf")
async def download_daily_summary_pdf(
    db: DbSession,
    current_user: CurrentUser,
    report_date: Optional[date] = None,
):
    """
    Download daily summary report as PDF.

    Includes:
    - Today's appointments overview
    - Revenue collected
    - No-shows and cancellations
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not report_date:
        report_date = date.today()

    service = get_report_service(db)
    pdf_bytes = await service.generate_daily_summary_pdf(
        clinic_id=clinic_id,
        report_date=report_date,
    )

    filename = f"daily_summary_{report_date.strftime('%Y-%m-%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/monthly/pdf")
async def download_monthly_report_pdf(
    db: DbSession,
    current_user: CurrentUser,
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """
    Download comprehensive monthly analytics report as PDF.

    Includes:
    - Monthly summary metrics
    - Revenue trends
    - Doctor utilization
    - Patient statistics
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    today = date.today()
    if not year:
        year = today.year
    if not month:
        month = today.month

    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12",
        )

    service = get_report_service(db)
    pdf_bytes = await service.generate_monthly_report_pdf(
        clinic_id=clinic_id,
        year=year,
        month=month,
    )

    filename = f"monthly_report_{year}-{month:02d}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/revenue/pdf")
async def download_revenue_report_pdf(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    doctor_id: Optional[UUID] = None,
):
    """
    Download detailed revenue report as PDF.

    Includes:
    - Revenue summary
    - Daily breakdown
    - Collection metrics
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_report_service(db)
    pdf_bytes = await service.generate_revenue_report_pdf(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
        doctor_id=doctor_id,
    )

    filename = f"revenue_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ========== Excel Export Endpoints ==========

@router.get("/appointments/excel")
async def download_appointments_excel(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    doctor_id: Optional[UUID] = None,
):
    """
    Download appointments report as Excel.

    Includes all appointment data with patient and doctor details.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_report_service(db)
    excel_bytes = await service.generate_appointments_excel(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
        doctor_id=doctor_id,
    )

    filename = f"appointments_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(excel_bytes)),
        },
    )


@router.get("/revenue/excel")
async def download_revenue_excel(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Download comprehensive revenue report as Excel.

    Includes:
    - Summary sheet
    - Daily breakdown with chart
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_report_service(db)
    excel_bytes = await service.generate_revenue_excel(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
    )

    filename = f"revenue_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(excel_bytes)),
        },
    )


@router.get("/doctors/utilization/excel")
async def download_doctor_utilization_excel(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Download doctor utilization report as Excel.

    Shows utilization metrics for all doctors.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_report_service(db)
    excel_bytes = await service.generate_doctor_utilization_excel(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
    )

    filename = f"doctor_utilization_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(excel_bytes)),
        },
    )


@router.get("/patients/demographics/excel")
async def download_patient_demographics_excel(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Download patient demographics report as Excel.

    Includes gender and city breakdowns.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_report_service(db)
    excel_bytes = await service.generate_patient_demographics_excel(
        clinic_id=clinic_id,
    )

    filename = f"patient_demographics_{date.today().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(excel_bytes)),
        },
    )


# ========== Report Metadata ==========

class ReportInfo(BaseModel):
    """Report metadata."""
    id: str
    name: str
    description: str
    formats: list[str]
    parameters: list[str]


@router.get("/available", response_model=list[ReportInfo])
async def list_available_reports(
    current_user: CurrentUser,
):
    """
    List all available reports.

    Returns metadata about each report type including
    supported formats and required parameters.
    """
    return [
        ReportInfo(
            id="daily_summary",
            name="Daily Summary",
            description="Overview of a single day's appointments and revenue",
            formats=["pdf"],
            parameters=["report_date"],
        ),
        ReportInfo(
            id="monthly_analytics",
            name="Monthly Analytics",
            description="Comprehensive monthly analysis with trends and insights",
            formats=["pdf"],
            parameters=["year", "month"],
        ),
        ReportInfo(
            id="revenue",
            name="Revenue Report",
            description="Detailed revenue breakdown with daily metrics",
            formats=["pdf", "excel"],
            parameters=["period", "start_date", "end_date", "doctor_id"],
        ),
        ReportInfo(
            id="appointments",
            name="Appointments Export",
            description="Full appointment data export with patient details",
            formats=["excel"],
            parameters=["period", "start_date", "end_date", "doctor_id"],
        ),
        ReportInfo(
            id="doctor_utilization",
            name="Doctor Utilization",
            description="Doctor productivity and utilization metrics",
            formats=["excel"],
            parameters=["period", "start_date", "end_date"],
        ),
        ReportInfo(
            id="patient_demographics",
            name="Patient Demographics",
            description="Patient population analysis by gender and location",
            formats=["excel"],
            parameters=[],
        ),
    ]
