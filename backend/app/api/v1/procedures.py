"""
Procedure & Intervention Tracking API endpoints.

Phase 9: REST API for flexible procedure tracking across all specialties.
"""

from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.models.procedure import ProcedureOutcome, ProcedureSeverity
from app.schemas.procedure import (
    ProcedureCreate,
    ProcedureUpdate,
    ProcedureResponse,
    ProcedureListResponse,
    ProcedureStats,
    ProcedureTypeCount,
    DoctorProcedureStats,
    ProcedureTrend,
    ProcedureQuickLog,
    ProcedureTemplatesResponse,
    ProcedureCategoryTemplate,
)
from app.services.procedures import (
    ProcedureService,
    ProcedureFilter,
    get_procedure_service,
)

router = APIRouter()


# ========== Response Models ==========

class ProcedureListWithCount(BaseModel):
    """Paginated procedure list response."""

    items: list[ProcedureListResponse]
    total: int
    limit: int
    offset: int


class ConsumablesUsageResponse(BaseModel):
    """Consumables usage response."""

    period_start: date
    period_end: date
    usage: dict


class PatientProcedureSummary(BaseModel):
    """Patient procedure summary response."""

    patient_id: UUID
    summary: dict


# ========== Helper Functions ==========

def get_date_range(period: str) -> tuple[date, date]:
    """Get date range from period string."""
    today = date.today()

    if period == "today":
        return today, today
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


# ========== CRUD Endpoints ==========

@router.post("", response_model=ProcedureResponse, status_code=status.HTTP_201_CREATED)
async def create_procedure(
    data: ProcedureCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create a new procedure record.

    Use this to log any procedure performed on a patient:
    - Cardiology: Echo, Angioplasty, Stent placement
    - Orthopedics: Surgery, Joint replacement
    - Ophthalmology: Cataract, LASIK
    - Any specialty: Custom procedures
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_procedure_service(db)
    procedure = await service.create(clinic_id, data)

    return ProcedureResponse(
        **procedure.__dict__,
        patient_name=procedure.patient.full_name if procedure.patient else None,
        doctor_name=procedure.doctor.name if procedure.doctor else None,
    )


@router.post("/quick", response_model=ProcedureResponse, status_code=status.HTTP_201_CREATED)
async def quick_log_procedure(
    data: ProcedureQuickLog,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Quick log a procedure with minimal fields.

    Ideal for rapid logging during busy clinic hours.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Convert quick log to full create
    create_data = ProcedureCreate(
        patient_id=data.patient_id,
        doctor_id=current_user.id,  # Assume current user is the doctor
        category=data.category,
        procedure_type=data.procedure_type,
        name=data.name,
        outcome=data.outcome,
        notes=data.notes,
        consumables=data.consumables,
        billed_amount=data.billed_amount,
    )

    service = get_procedure_service(db)
    procedure = await service.create(clinic_id, create_data)

    return ProcedureResponse(
        **procedure.__dict__,
        patient_name=procedure.patient.full_name if procedure.patient else None,
        doctor_name=procedure.doctor.name if procedure.doctor else None,
    )


@router.get("/{procedure_id}", response_model=ProcedureResponse)
async def get_procedure(
    procedure_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a procedure by ID."""
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_procedure_service(db)
    procedure = await service.get_by_id(procedure_id, clinic_id)

    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedure not found",
        )

    return ProcedureResponse(
        **procedure.__dict__,
        patient_name=procedure.patient.full_name if procedure.patient else None,
        doctor_name=procedure.doctor.name if procedure.doctor else None,
    )


@router.put("/{procedure_id}", response_model=ProcedureResponse)
async def update_procedure(
    procedure_id: UUID,
    data: ProcedureUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update a procedure."""
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_procedure_service(db)
    procedure = await service.update(procedure_id, clinic_id, data)

    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedure not found",
        )

    return ProcedureResponse(
        **procedure.__dict__,
        patient_name=procedure.patient.full_name if procedure.patient else None,
        doctor_name=procedure.doctor.name if procedure.doctor else None,
    )


@router.delete("/{procedure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procedure(
    procedure_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a procedure."""
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_procedure_service(db)
    deleted = await service.delete(procedure_id, clinic_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedure not found",
        )


@router.get("", response_model=ProcedureListWithCount)
async def list_procedures(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    category: Optional[str] = None,
    procedure_type: Optional[str] = None,
    outcome: Optional[ProcedureOutcome] = None,
    period: str = Query("month", regex="^(today|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_billable: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List procedures with filters.

    Supports filtering by:
    - Patient
    - Doctor
    - Category (Cardiology, Orthopedics, etc.)
    - Procedure type (Echo, Stent, etc.)
    - Outcome
    - Date range
    - Billable status
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    filters = ProcedureFilter(
        clinic_id=clinic_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        category=category,
        procedure_type=procedure_type,
        outcome=outcome,
        start_date=start_date,
        end_date=end_date,
        is_billable=is_billable,
    )

    service = get_procedure_service(db)
    procedures, total = await service.list(filters, limit, offset)

    items = [
        ProcedureListResponse(
            id=p.id,
            patient_id=p.patient_id,
            patient_name=p.patient.full_name if p.patient else "Unknown",
            doctor_id=p.doctor_id,
            doctor_name=p.doctor.name if p.doctor else "Unknown",
            category=p.category,
            procedure_type=p.procedure_type,
            name=p.name,
            performed_at=p.performed_at,
            outcome=p.outcome,
            severity=p.severity,
            is_billable=p.is_billable,
            billed_amount=float(p.billed_amount) if p.billed_amount else None,
        )
        for p in procedures
    ]

    return ProcedureListWithCount(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ========== Patient Procedures ==========

@router.get("/patient/{patient_id}", response_model=list[ProcedureListResponse])
async def get_patient_procedures(
    patient_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get all procedures for a patient.

    Use case: View patient's procedure history.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_procedure_service(db)
    procedures = await service.get_patient_procedures(patient_id, clinic_id, category, limit)

    return [
        ProcedureListResponse(
            id=p.id,
            patient_id=p.patient_id,
            patient_name=p.patient.full_name if p.patient else "Unknown",
            doctor_id=p.doctor_id,
            doctor_name=p.doctor.name if p.doctor else "Unknown",
            category=p.category,
            procedure_type=p.procedure_type,
            name=p.name,
            performed_at=p.performed_at,
            outcome=p.outcome,
            severity=p.severity,
            is_billable=p.is_billable,
            billed_amount=float(p.billed_amount) if p.billed_amount else None,
        )
        for p in procedures
    ]


@router.get("/patient/{patient_id}/summary", response_model=PatientProcedureSummary)
async def get_patient_procedure_summary(
    patient_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get summary of all procedures for a patient.

    Returns counts by category and type.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_procedure_service(db)
    summary = await service.get_patient_procedure_summary(patient_id, clinic_id)

    return PatientProcedureSummary(
        patient_id=patient_id,
        summary=summary,
    )


# ========== Analytics Endpoints ==========

@router.get("/analytics/stats", response_model=ProcedureStats)
async def get_procedure_stats(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    doctor_id: Optional[UUID] = None,
):
    """
    Get procedure statistics.

    Use case: "How many echos did I do this month?"
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_procedure_service(db)
    stats = await service.get_stats(clinic_id, start_date, end_date, doctor_id)

    return stats


@router.get("/analytics/types", response_model=list[ProcedureTypeCount])
async def get_procedure_type_counts(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
):
    """
    Get procedure counts by type.

    Use case: "How many stents vs echos vs angioplasties this month?"
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_procedure_service(db)
    counts = await service.get_type_counts(clinic_id, start_date, end_date, category)

    return counts


@router.get("/analytics/doctors", response_model=list[DoctorProcedureStats])
async def get_doctor_procedure_stats(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(today|week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Get procedure statistics per doctor.

    Use case: "Which doctor does the most procedures?"
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_procedure_service(db)
    stats = await service.get_doctor_stats(clinic_id, start_date, end_date)

    return stats


@router.get("/analytics/trend", response_model=list[ProcedureTrend])
async def get_procedure_trend(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(week|month|quarter)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
):
    """
    Get day-by-day procedure trend.

    Use case: "Show me procedure trends for the month."
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_procedure_service(db)
    trend = await service.get_daily_trend(clinic_id, start_date, end_date, category)

    return trend


@router.get("/analytics/consumables", response_model=ConsumablesUsageResponse)
async def get_consumables_usage(
    db: DbSession,
    current_user: CurrentUser,
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
):
    """
    Get consumables usage summary.

    Use case: "How many Xience stents did we use this month?"
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    if not start_date or not end_date:
        start_date, end_date = get_date_range(period)

    service = get_procedure_service(db)
    usage = await service.get_consumables_usage(clinic_id, start_date, end_date, category)

    return ConsumablesUsageResponse(
        period_start=start_date,
        period_end=end_date,
        usage=usage,
    )


# ========== Templates ==========

@router.get("/templates", response_model=ProcedureTemplatesResponse)
async def get_procedure_templates(
    current_user: CurrentUser,
):
    """
    Get predefined procedure templates.

    Returns templates for common specialties:
    - Cardiology
    - Orthopedics
    - Ophthalmology
    - Dermatology
    - Gastroenterology
    """
    from app.models.procedure import PROCEDURE_TEMPLATES

    templates = {}
    for key, value in PROCEDURE_TEMPLATES.items():
        templates[key] = ProcedureCategoryTemplate(
            category=value["category"],
            types=value["types"],
        )

    return ProcedureTemplatesResponse(templates=templates)


@router.get("/templates/{category}")
async def get_category_template(
    category: str,
    current_user: CurrentUser,
):
    """
    Get templates for a specific category.

    Example: /templates/cardiology
    """
    from app.models.procedure import PROCEDURE_TEMPLATES

    template = PROCEDURE_TEMPLATES.get(category.lower())
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No template found for category: {category}",
        )

    return ProcedureCategoryTemplate(
        category=template["category"],
        types=template["types"],
    )
