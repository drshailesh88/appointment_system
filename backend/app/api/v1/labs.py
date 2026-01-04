"""
Lab results API endpoints.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.integrations.lab_integration import (
    LabOrderRequest,
    get_lab_integration_service,
)
from app.models.doctor import Doctor
from app.models.lab_result import (
    LabOrder,
    LabOrderStatus,
    LabReport,
    LabResult,
    LabResultStatus,
)
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.lab import (
    LabOrderCreate,
    LabOrderFilter,
    LabOrderListResponse,
    LabOrderResponse,
    LabOrderUpdate,
    LabReportResponse,
    LabReportUploadResponse,
    LabResultCreate,
    LabResultFilter,
    LabResultResponse,
    LabResultTrendPoint,
    LabResultTrendResponse,
    LabStatistics,
)
from app.services.lab_parser import LabParserFactory

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Lab Orders
# ============================================================


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    db: DbSession,
    current_user: CurrentUser,
    order_in: LabOrderCreate,
) -> LabOrder:
    """Create a new lab order."""
    # Verify doctor exists
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.id == order_in.doctor_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == order_in.patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Create order
    lab_order = LabOrder(
        patient_id=order_in.patient_id,
        doctor_id=order_in.doctor_id,
        appointment_id=order_in.appointment_id,
        order_date=datetime.now(timezone.utc),
        tests_ordered=order_in.tests_ordered,
        priority=order_in.priority.value,
        status=LabOrderStatus.ORDERED.value,
        clinical_notes=order_in.clinical_notes,
        diagnosis_codes=order_in.diagnosis_codes,
        expected_completion=order_in.expected_completion,
        lab_provider=order_in.lab_provider,
    )

    db.add(lab_order)
    await db.commit()
    await db.refresh(lab_order)

    # Optionally integrate with external lab
    if order_in.lab_provider:
        try:
            lab_service = get_lab_integration_service()
            provider_request = LabOrderRequest(
                patient_id=str(patient.id),
                patient_name=f"{patient.first_name} {patient.last_name}",
                tests=order_in.tests_ordered,
                priority=order_in.priority.value,
                clinical_notes=order_in.clinical_notes,
                diagnosis_codes=order_in.diagnosis_codes,
            )

            provider_response = await lab_service.create_order(
                provider_request,
                provider_name=order_in.lab_provider,
            )

            # Update order with provider details
            lab_order.lab_order_id = provider_response.order_id
            lab_order.metadata = provider_response.metadata
            await db.commit()

        except Exception as e:
            logger.error(f"Failed to create order with lab provider: {e}")
            # Don't fail the entire request, just log the error

    logger.info(f"Created lab order {lab_order.id}")
    return lab_order


@router.get("/orders/{order_id}", response_model=LabOrderResponse)
async def get_lab_order(
    db: DbSession,
    current_user: CurrentUser,
    order_id: UUID,
) -> LabOrder:
    """Get a specific lab order."""
    result = await db.execute(
        select(LabOrder)
        .options(selectinload(LabOrder.patient))
        .options(selectinload(LabOrder.doctor))
        .options(selectinload(LabOrder.results))
        .where(LabOrder.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != order.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Enrich response
    order.patient_name = f"{order.patient.first_name} {order.patient.last_name}"
    order.doctor_name = order.doctor.full_name
    order.results_count = len(order.results)
    order.abnormal_count = sum(1 for r in order.results if r.is_abnormal)

    return order


@router.patch("/orders/{order_id}", response_model=LabOrderResponse)
async def update_lab_order(
    db: DbSession,
    current_user: CurrentUser,
    order_id: UUID,
    order_update: LabOrderUpdate,
) -> LabOrder:
    """Update a lab order."""
    result = await db.execute(
        select(LabOrder)
        .options(selectinload(LabOrder.doctor))
        .where(LabOrder.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != order.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(order, field):
            setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    logger.info(f"Updated lab order {order_id}")
    return order


@router.get("/patient/{patient_id}/orders", response_model=LabOrderListResponse)
async def get_patient_lab_orders(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Get all lab orders for a patient."""
    # Verify patient exists and check access
    patient_result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Build query
    query = (
        select(LabOrder)
        .options(selectinload(LabOrder.patient))
        .options(selectinload(LabOrder.doctor))
        .options(selectinload(LabOrder.results))
        .where(LabOrder.patient_id == patient_id)
    )

    if status:
        query = query.where(LabOrder.status == status)

    query = query.order_by(LabOrder.order_date.desc())

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Paginate
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    orders = result.scalars().all()

    # Enrich responses
    for order in orders:
        order.patient_name = f"{order.patient.first_name} {order.patient.last_name}"
        order.doctor_name = order.doctor.full_name
        order.results_count = len(order.results)
        order.abnormal_count = sum(1 for r in order.results if r.is_abnormal)

    return {"orders": orders, "total": total}


# ============================================================
# Lab Results
# ============================================================


@router.post("/results", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    db: DbSession,
    current_user: CurrentUser,
    result_in: LabResultCreate,
) -> LabResult:
    """Create a lab result manually."""
    # Verify order exists
    order_result = await db.execute(
        select(LabOrder)
        .options(selectinload(LabOrder.doctor))
        .where(LabOrder.id == result_in.order_id)
    )
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != order.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Create result
    lab_result = LabResult(**result_in.model_dump())
    db.add(lab_result)

    # Update order status if needed
    if order.status == LabOrderStatus.ORDERED.value:
        order.status = LabOrderStatus.IN_PROGRESS.value

    await db.commit()
    await db.refresh(lab_result)

    logger.info(f"Created lab result {lab_result.id}")
    return lab_result


@router.get("/results/{result_id}", response_model=LabResultResponse)
async def get_lab_result(
    db: DbSession,
    current_user: CurrentUser,
    result_id: UUID,
) -> LabResult:
    """Get a specific lab result."""
    result = await db.execute(
        select(LabResult)
        .options(selectinload(LabResult.order).selectinload(LabOrder.doctor))
        .where(LabResult.id == result_id)
    )
    lab_result = result.scalar_one_or_none()

    if not lab_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab result not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != lab_result.order.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return lab_result


@router.get("/patient/{patient_id}/results", response_model=list[LabResultResponse])
async def get_patient_lab_results(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID,
    test_name: str | None = None,
    test_category: str | None = None,
    is_abnormal: bool | None = None,
    limit: int = 100,
) -> list[LabResult]:
    """Get all lab results for a patient."""
    # Verify patient and access
    patient_result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Build query
    query = (
        select(LabResult)
        .join(LabOrder)
        .where(LabOrder.patient_id == patient_id)
    )

    if test_name:
        query = query.where(LabResult.test_name.ilike(f"%{test_name}%"))

    if test_category:
        query = query.where(LabResult.test_category == test_category)

    if is_abnormal is not None:
        query = query.where(LabResult.is_abnormal == is_abnormal)

    query = query.order_by(LabResult.result_date.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/results/{result_id}/trends", response_model=LabResultTrendResponse)
async def get_lab_result_trends(
    db: DbSession,
    current_user: CurrentUser,
    result_id: UUID,
    months: int = 12,
) -> LabResultTrendResponse:
    """Get historical trends for a specific test."""
    # Get the reference result
    ref_result = await db.execute(
        select(LabResult)
        .options(selectinload(LabResult.order).selectinload(LabOrder.doctor))
        .where(LabResult.id == result_id)
    )
    reference = ref_result.scalar_one_or_none()

    if not reference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab result not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != reference.order.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get historical results for same test
    from datetime import timedelta

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30 * months)

    query = (
        select(LabResult)
        .join(LabOrder)
        .where(
            and_(
                LabOrder.patient_id == reference.order.patient_id,
                LabResult.test_name == reference.test_name,
                LabResult.value_numeric.isnot(None),
                LabResult.result_date >= cutoff_date,
            )
        )
        .order_by(LabResult.result_date.asc())
    )

    result = await db.execute(query)
    historical_results = result.scalars().all()

    # Build trend data
    data_points = [
        LabResultTrendPoint(
            date=r.result_date or r.created_at,
            value=r.value_numeric,
            is_abnormal=r.is_abnormal,
        )
        for r in historical_results
        if r.value_numeric is not None
    ]

    return LabResultTrendResponse(
        test_name=reference.test_name,
        unit=reference.unit,
        reference_range_min=reference.reference_range_min,
        reference_range_max=reference.reference_range_max,
        data_points=data_points,
    )


# ============================================================
# Lab Reports (Upload & Parse)
# ============================================================


@router.post("/results/upload", response_model=LabReportUploadResponse)
async def upload_lab_results(
    db: DbSession,
    current_user: CurrentUser,
    order_id: UUID,
    file: UploadFile = File(...),
) -> dict:
    """Upload and parse lab results (PDF/HL7)."""
    # Verify order exists
    order_result = await db.execute(
        select(LabOrder)
        .options(selectinload(LabOrder.doctor))
        .where(LabOrder.id == order_id)
    )
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != order.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Read file content
    content = await file.read()

    # Detect file type
    file_type = LabParserFactory.detect_file_type(content)

    # Save file
    upload_dir = Path("/var/lab_reports/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{order_id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)

    # Create report record
    lab_report = LabReport(
        order_id=order_id,
        report_type=file_type,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type,
        received_at=datetime.now(timezone.utc),
    )
    db.add(lab_report)

    # Parse results
    parsing_errors = []
    results_created = 0

    try:
        parser = LabParserFactory.create_parser(file_type)
        parsed_report = parser.parse(content)

        # Store parsed data
        lab_report.parsed_data = {
            "patient_name": parsed_report.patient_name,
            "patient_id": parsed_report.patient_id,
            "lab_order_id": parsed_report.lab_order_id,
            "report_date": parsed_report.report_date.isoformat() if parsed_report.report_date else None,
            "lab_provider": parsed_report.lab_provider,
        }
        lab_report.raw_content = parsed_report.raw_text[:10000]  # Limit size

        # Create result records
        for parsed_result in parsed_report.results:
            try:
                lab_result = LabResult(
                    order_id=order_id,
                    test_name=parsed_result.test_name,
                    test_code=parsed_result.test_code,
                    test_category=parsed_result.test_category,
                    value=parsed_result.value,
                    value_numeric=parsed_result.value_numeric,
                    unit=parsed_result.unit,
                    reference_range_min=parsed_result.reference_range_min,
                    reference_range_max=parsed_result.reference_range_max,
                    reference_range_text=parsed_result.reference_range_text,
                    is_abnormal=parsed_result.is_abnormal,
                    abnormal_flag=parsed_result.abnormal_flag,
                    status=LabResultStatus.FINAL.value,
                    result_date=parsed_report.report_date or datetime.now(timezone.utc),
                    notes=parsed_result.notes,
                )
                db.add(lab_result)
                results_created += 1

            except Exception as e:
                parsing_errors.append(f"Error creating result for {parsed_result.test_name}: {e}")
                logger.error(f"Error creating lab result: {e}")

        # Update order status
        if results_created > 0:
            order.status = LabOrderStatus.COMPLETED.value

    except Exception as e:
        parsing_errors.append(f"Parsing error: {e}")
        logger.error(f"Error parsing lab report: {e}")

    await db.commit()
    await db.refresh(lab_report)

    logger.info(f"Uploaded lab report {lab_report.id}, created {results_created} results")

    return {
        "order_id": order_id,
        "report_id": lab_report.id,
        "results_created": results_created,
        "parsing_errors": parsing_errors,
    }


@router.get("/orders/{order_id}/reports", response_model=list[LabReportResponse])
async def get_order_reports(
    db: DbSession,
    current_user: CurrentUser,
    order_id: UUID,
) -> list[LabReport]:
    """Get all reports for a lab order."""
    # Verify order and access
    order_result = await db.execute(
        select(LabOrder)
        .options(selectinload(LabOrder.doctor))
        .where(LabOrder.id == order_id)
    )
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != order.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    result = await db.execute(
        select(LabReport).where(LabReport.order_id == order_id)
    )
    return result.scalars().all()


# ============================================================
# Statistics
# ============================================================


@router.get("/statistics", response_model=LabStatistics)
async def get_lab_statistics(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: UUID | None = None,
) -> LabStatistics:
    """Get lab statistics."""
    # Build base query
    orders_query = select(LabOrder)
    results_query = select(LabResult).join(LabOrder)

    # Filter by clinic
    if current_user.role != UserRole.ADMIN.value:
        orders_query = orders_query.join(Doctor).where(
            Doctor.clinic_id == current_user.clinic_id
        )
        results_query = results_query.join(Doctor).where(
            Doctor.clinic_id == current_user.clinic_id
        )

    # Filter by doctor
    if doctor_id:
        orders_query = orders_query.where(LabOrder.doctor_id == doctor_id)
        results_query = results_query.where(LabOrder.doctor_id == doctor_id)

    # Count orders
    total_orders_result = await db.execute(
        select(func.count()).select_from(orders_query.subquery())
    )
    total_orders = total_orders_result.scalar_one()

    # Count by status
    pending_result = await db.execute(
        select(func.count())
        .select_from(orders_query.where(
            LabOrder.status.in_([
                LabOrderStatus.ORDERED.value,
                LabOrderStatus.SAMPLE_COLLECTED.value,
                LabOrderStatus.IN_PROGRESS.value,
            ])
        ).subquery())
    )
    pending_orders = pending_result.scalar_one()

    completed_result = await db.execute(
        select(func.count())
        .select_from(orders_query.where(
            LabOrder.status == LabOrderStatus.COMPLETED.value
        ).subquery())
    )
    completed_orders = completed_result.scalar_one()

    # Count results
    total_results_result = await db.execute(
        select(func.count()).select_from(results_query.subquery())
    )
    total_results = total_results_result.scalar_one()

    abnormal_results_result = await db.execute(
        select(func.count())
        .select_from(results_query.where(LabResult.is_abnormal == True).subquery())
    )
    abnormal_results = abnormal_results_result.scalar_one()

    # Most ordered tests (top 10)
    most_ordered_query = (
        select(
            func.unnest(LabOrder.tests_ordered).label("test"),
            func.count().label("count"),
        )
        .select_from(orders_query.subquery())
        .group_by("test")
        .order_by(func.count().desc())
        .limit(10)
    )

    most_ordered_result = await db.execute(most_ordered_query)
    most_ordered_tests = [
        {"test": row[0], "count": row[1]}
        for row in most_ordered_result.all()
    ]

    return LabStatistics(
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        total_results=total_results,
        abnormal_results=abnormal_results,
        most_ordered_tests=most_ordered_tests,
        average_turnaround_hours=None,  # TODO: Calculate if needed
    )
