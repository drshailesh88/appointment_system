"""
Reports API endpoints.

Provides report generation and scheduling functionality:
- Generate reports on-demand
- Schedule recurring reports
- Manage report templates
- Download generated reports
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.scheduled_report import (
    ScheduledReport,
    ReportType,
    ReportFormat,
    ReportFrequency,
)
from app.services.report_generator import get_report_generator
from app.services.report_scheduler import get_report_scheduler

router = APIRouter()


# --- Pydantic Models ---

class ReportTemplateModel(BaseModel):
    """Report template information."""
    type: str
    name: str
    description: str
    supported_formats: list[str]
    default_format: str
    parameters: list[dict]


class GenerateReportRequest(BaseModel):
    """Request to generate a report."""
    report_type: str = Field(..., description="Type of report to generate")
    format: str = Field(default="pdf", description="Output format (pdf, xlsx, csv)")
    start_date: date = Field(..., description="Report period start date")
    end_date: date = Field(..., description="Report period end date")
    parameters: Optional[dict] = Field(default=None, description="Additional parameters")


class GenerateReportResponse(BaseModel):
    """Response for report generation."""
    success: bool
    message: str
    filename: str
    size_bytes: int


class ScheduledReportCreate(BaseModel):
    """Create scheduled report request."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    report_type: str
    report_format: str = Field(default="pdf")
    frequency: str = Field(default="weekly")
    cron_expression: Optional[str] = None
    recipients: list[EmailStr]
    parameters: Optional[dict] = None


class ScheduledReportUpdate(BaseModel):
    """Update scheduled report request."""
    name: Optional[str] = None
    description: Optional[str] = None
    report_format: Optional[str] = None
    frequency: Optional[str] = None
    cron_expression: Optional[str] = None
    recipients: Optional[list[EmailStr]] = None
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None


class ScheduledReportResponse(BaseModel):
    """Scheduled report response."""
    id: str
    name: str
    description: Optional[str]
    report_type: str
    report_format: str
    frequency: str
    cron_expression: Optional[str]
    recipients: list[str]
    parameters: Optional[dict]
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    last_run_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- API Endpoints ---

@router.get("/templates", response_model=list[ReportTemplateModel])
async def get_report_templates():
    """
    Get list of available report templates.

    Returns information about all available report types.
    """
    templates = [
        {
            "type": ReportType.DAILY_SUMMARY.value,
            "name": "Daily Summary",
            "description": "Daily appointment and revenue summary",
            "supported_formats": ["pdf", "xlsx", "csv"],
            "default_format": "pdf",
            "parameters": [],
        },
        {
            "type": ReportType.WEEKLY_SUMMARY.value,
            "name": "Weekly Summary",
            "description": "Weekly performance report with trends and doctor metrics",
            "supported_formats": ["pdf", "xlsx", "csv"],
            "default_format": "pdf",
            "parameters": [],
        },
        {
            "type": ReportType.MONTHLY_SUMMARY.value,
            "name": "Monthly Summary",
            "description": "Comprehensive monthly practice report",
            "supported_formats": ["pdf", "xlsx", "csv"],
            "default_format": "pdf",
            "parameters": [],
        },
        {
            "type": ReportType.DOCTOR_PERFORMANCE.value,
            "name": "Doctor Performance",
            "description": "Individual doctor performance metrics",
            "supported_formats": ["pdf", "xlsx", "csv"],
            "default_format": "pdf",
            "parameters": [
                {
                    "name": "doctor_id",
                    "type": "uuid",
                    "required": False,
                    "description": "Filter by specific doctor (optional)",
                }
            ],
        },
        {
            "type": ReportType.REVENUE_REPORT.value,
            "name": "Revenue Report",
            "description": "Detailed revenue analysis with daily trends",
            "supported_formats": ["pdf", "xlsx", "csv"],
            "default_format": "pdf",
            "parameters": [],
        },
        {
            "type": ReportType.PATIENT_DEMOGRAPHICS.value,
            "name": "Patient Demographics",
            "description": "Patient population breakdown by gender, age, and location",
            "supported_formats": ["pdf", "xlsx", "csv"],
            "default_format": "pdf",
            "parameters": [],
        },
        {
            "type": ReportType.NO_SHOW_ANALYSIS.value,
            "name": "No-Show Analysis",
            "description": "Analysis of no-show patterns by day and time",
            "supported_formats": ["pdf", "xlsx", "csv"],
            "default_format": "pdf",
            "parameters": [],
        },
    ]

    return [ReportTemplateModel(**t) for t in templates]


@router.post("/generate", response_class=Response)
async def generate_report(
    request: GenerateReportRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Generate a report on-demand.

    Returns the report file directly for download.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Validate report type
    try:
        ReportType(request.report_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type: {request.report_type}",
        )

    # Validate format
    try:
        ReportFormat(request.format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {request.format}",
        )

    # Validate date range
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    try:
        # Generate report
        generator = get_report_generator(db)
        report_bytes = await generator.generate_report(
            clinic_id=clinic_id,
            report_type=request.report_type,
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            parameters=request.parameters or {},
        )

        # Determine filename and content type
        date_str = request.end_date.strftime('%Y%m%d')
        if request.format == ReportFormat.PDF.value:
            filename = f"{request.report_type}_{date_str}.pdf"
            content_type = "application/pdf"
        elif request.format == ReportFormat.EXCEL.value:
            filename = f"{request.report_type}_{date_str}.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            filename = f"{request.report_type}_{date_str}.csv"
            content_type = "text/csv"

        # Return file
        return Response(
            content=report_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/scheduled", response_model=list[ScheduledReportResponse])
async def list_scheduled_reports(
    db: DbSession,
    current_user: CurrentUser,
    active_only: bool = Query(default=True, description="Show only active reports"),
):
    """
    Get list of scheduled reports for the current clinic.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Build query
    query = select(ScheduledReport).where(ScheduledReport.clinic_id == clinic_id)
    if active_only:
        query = query.where(ScheduledReport.is_active == True)

    result = await db.execute(query.order_by(ScheduledReport.created_at.desc()))
    reports = result.scalars().all()

    return [
        ScheduledReportResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            report_type=r.report_type,
            report_format=r.report_format,
            frequency=r.frequency,
            cron_expression=r.cron_expression,
            recipients=r.recipients.get('emails', []) if isinstance(r.recipients, dict) else r.recipients,
            parameters=r.parameters,
            is_active=r.is_active,
            last_run_at=r.last_run_at,
            next_run_at=r.next_run_at,
            last_run_status=r.last_run_status,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.post("/scheduled", response_model=ScheduledReportResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_report(
    request: ScheduledReportCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create a new scheduled report.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Validate report type
    try:
        ReportType(request.report_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type: {request.report_type}",
        )

    # Validate format
    try:
        ReportFormat(request.report_format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {request.report_format}",
        )

    # Validate frequency
    try:
        ReportFrequency(request.frequency)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid frequency: {request.frequency}",
        )

    # Create scheduled report
    scheduled_report = ScheduledReport(
        clinic_id=clinic_id,
        name=request.name,
        description=request.description,
        report_type=request.report_type,
        report_format=request.report_format,
        frequency=request.frequency,
        cron_expression=request.cron_expression,
        recipients={"emails": request.recipients},
        parameters=request.parameters,
        is_active=True,
        created_by_user_id=current_user.id,
    )

    db.add(scheduled_report)
    await db.commit()
    await db.refresh(scheduled_report)

    # Schedule it
    scheduler = get_report_scheduler()
    await scheduler.schedule_report(scheduled_report)

    # Update next_run_at in database
    await db.commit()
    await db.refresh(scheduled_report)

    return ScheduledReportResponse(
        id=str(scheduled_report.id),
        name=scheduled_report.name,
        description=scheduled_report.description,
        report_type=scheduled_report.report_type,
        report_format=scheduled_report.report_format,
        frequency=scheduled_report.frequency,
        cron_expression=scheduled_report.cron_expression,
        recipients=scheduled_report.recipients.get('emails', []),
        parameters=scheduled_report.parameters,
        is_active=scheduled_report.is_active,
        last_run_at=scheduled_report.last_run_at,
        next_run_at=scheduled_report.next_run_at,
        last_run_status=scheduled_report.last_run_status,
        created_at=scheduled_report.created_at,
    )


@router.get("/scheduled/{report_id}", response_model=ScheduledReportResponse)
async def get_scheduled_report(
    report_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get details of a specific scheduled report.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.id == report_id,
            ScheduledReport.clinic_id == clinic_id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found",
        )

    return ScheduledReportResponse(
        id=str(report.id),
        name=report.name,
        description=report.description,
        report_type=report.report_type,
        report_format=report.report_format,
        frequency=report.frequency,
        cron_expression=report.cron_expression,
        recipients=report.recipients.get('emails', []) if isinstance(report.recipients, dict) else report.recipients,
        parameters=report.parameters,
        is_active=report.is_active,
        last_run_at=report.last_run_at,
        next_run_at=report.next_run_at,
        last_run_status=report.last_run_status,
        created_at=report.created_at,
    )


@router.patch("/scheduled/{report_id}", response_model=ScheduledReportResponse)
async def update_scheduled_report(
    report_id: UUID,
    request: ScheduledReportUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Update a scheduled report.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.id == report_id,
            ScheduledReport.clinic_id == clinic_id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found",
        )

    # Update fields
    if request.name is not None:
        report.name = request.name
    if request.description is not None:
        report.description = request.description
    if request.report_format is not None:
        try:
            ReportFormat(request.report_format)
            report.report_format = request.report_format
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {request.report_format}",
            )
    if request.frequency is not None:
        try:
            ReportFrequency(request.frequency)
            report.frequency = request.frequency
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid frequency: {request.frequency}",
            )
    if request.cron_expression is not None:
        report.cron_expression = request.cron_expression
    if request.recipients is not None:
        report.recipients = {"emails": request.recipients}
    if request.parameters is not None:
        report.parameters = request.parameters
    if request.is_active is not None:
        report.is_active = request.is_active

    await db.commit()
    await db.refresh(report)

    # Reschedule if active, unschedule if inactive
    scheduler = get_report_scheduler()
    if report.is_active:
        await scheduler.schedule_report(report)
        await db.commit()
        await db.refresh(report)
    else:
        await scheduler.unschedule_report(report.id)

    return ScheduledReportResponse(
        id=str(report.id),
        name=report.name,
        description=report.description,
        report_type=report.report_type,
        report_format=report.report_format,
        frequency=report.frequency,
        cron_expression=report.cron_expression,
        recipients=report.recipients.get('emails', []),
        parameters=report.parameters,
        is_active=report.is_active,
        last_run_at=report.last_run_at,
        next_run_at=report.next_run_at,
        last_run_status=report.last_run_status,
        created_at=report.created_at,
    )


@router.delete("/scheduled/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_report(
    report_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Delete a scheduled report.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.id == report_id,
            ScheduledReport.clinic_id == clinic_id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found",
        )

    # Unschedule
    scheduler = get_report_scheduler()
    await scheduler.unschedule_report(report.id)

    # Delete from database
    await db.execute(
        delete(ScheduledReport).where(ScheduledReport.id == report_id)
    )
    await db.commit()


@router.post("/scheduled/{report_id}/run-now", response_class=Response)
async def run_scheduled_report_now(
    report_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
):
    """
    Generate a scheduled report immediately (on-demand).

    Uses the report's configured settings but allows custom date range.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.id == report_id,
            ScheduledReport.clinic_id == clinic_id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found",
        )

    try:
        # Generate report
        scheduler = get_report_scheduler()
        report_bytes = await scheduler.generate_report_now(
            report_id=report.id,
            start_date=start_date,
            end_date=end_date,
        )

        # Determine filename and content type
        date_str = (end_date or date.today()).strftime('%Y%m%d')
        if report.report_format == ReportFormat.PDF.value:
            filename = f"{report.name.replace(' ', '_')}_{date_str}.pdf"
            content_type = "application/pdf"
        elif report.report_format == ReportFormat.EXCEL.value:
            filename = f"{report.name.replace(' ', '_')}_{date_str}.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            filename = f"{report.name.replace(' ', '_')}_{date_str}.csv"
            content_type = "text/csv"

        return Response(
            content=report_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )
