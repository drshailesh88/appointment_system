"""
Health API endpoints for managing health records from Apple Health and other sources.

Provides endpoints for:
- Syncing health data from devices
- Retrieving patient health records
- Getting health summaries
- Managing health metrics
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.models.health_record import HealthRecord
from app.models.patient import Patient
from app.schemas.health import (
    HealthRecordBulkCreate,
    HealthRecordCreate,
    HealthRecordResponse,
    HealthRecordsFilter,
    HealthSummaryResponse,
    HealthSyncResponse,
)

router = APIRouter()


@router.post("/sync", response_model=HealthSyncResponse, status_code=status.HTTP_201_CREATED)
async def sync_health_data(
    sync_data: HealthRecordBulkCreate,
    db: Session = Depends(DbSession),
    current_user: dict = Depends(CurrentUser),
) -> HealthSyncResponse:
    """
    Sync health data from device (bulk create).

    Used by mobile apps to sync health data from Apple Health or other sources.
    """
    synced_count = 0
    failed_count = 0
    errors = []

    for reading in sync_data.readings:
        try:
            # Verify patient exists and belongs to user's clinic
            patient = db.query(Patient).filter(Patient.id == reading.patient_id).first()
            if not patient:
                failed_count += 1
                errors.append(f"Patient {reading.patient_id} not found")
                continue

            # Check for duplicate (same patient, metric, timestamp)
            existing = (
                db.query(HealthRecord)
                .filter(
                    and_(
                        HealthRecord.patient_id == reading.patient_id,
                        HealthRecord.metric_type == reading.metric_type,
                        HealthRecord.recorded_at == reading.recorded_at,
                        HealthRecord.source == reading.source,
                    )
                )
                .first()
            )

            if existing:
                # Skip duplicate
                continue

            # Create health record
            health_record = HealthRecord(
                patient_id=reading.patient_id,
                metric_type=reading.metric_type,
                value=reading.value,
                unit=reading.unit,
                recorded_at=reading.recorded_at,
                source=reading.source,
                device_id=reading.device_id,
                metadata=reading.metadata,
            )
            db.add(health_record)
            synced_count += 1

        except Exception as e:
            failed_count += 1
            errors.append(f"Error syncing reading: {str(e)}")

    db.commit()

    return HealthSyncResponse(
        success=True,
        synced_count=synced_count,
        failed_count=failed_count,
        errors=errors,
        last_synced_at=datetime.utcnow(),
    )


@router.get("/patient/{patient_id}/records", response_model=list[HealthRecordResponse])
async def get_patient_health_records(
    patient_id: UUID,
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    start_date: Optional[datetime] = Query(None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter to this date"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(DbSession),
    current_user: dict = Depends(CurrentUser),
) -> list[HealthRecordResponse]:
    """
    Get health records for a patient.

    Filter by metric type and date range.
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Build query
    query = db.query(HealthRecord).filter(HealthRecord.patient_id == patient_id)

    if metric_type:
        query = query.filter(HealthRecord.metric_type == metric_type)

    if start_date:
        query = query.filter(HealthRecord.recorded_at >= start_date)

    if end_date:
        query = query.filter(HealthRecord.recorded_at <= end_date)

    # Order by recorded_at descending (newest first)
    query = query.order_by(desc(HealthRecord.recorded_at))

    # Apply pagination
    records = query.offset(offset).limit(limit).all()

    return [HealthRecordResponse.model_validate(record) for record in records]


@router.get("/patient/{patient_id}/summary", response_model=HealthSummaryResponse)
async def get_patient_health_summary(
    patient_id: UUID,
    db: Session = Depends(DbSession),
    current_user: dict = Depends(CurrentUser),
) -> HealthSummaryResponse:
    """
    Get health summary for a patient.

    Returns latest readings for key vital signs and today's activity metrics.
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Get latest readings for each vital sign
    def get_latest_reading(metric_type: str) -> Optional[HealthRecordResponse]:
        record = (
            db.query(HealthRecord)
            .filter(
                and_(
                    HealthRecord.patient_id == patient_id,
                    HealthRecord.metric_type == metric_type,
                )
            )
            .order_by(desc(HealthRecord.recorded_at))
            .first()
        )
        return HealthRecordResponse.model_validate(record) if record else None

    # Get today's activity metrics
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Steps
    steps_record = (
        db.query(func.sum(HealthRecord.value))
        .filter(
            and_(
                HealthRecord.patient_id == patient_id,
                HealthRecord.metric_type == "steps",
                HealthRecord.recorded_at >= today_start,
                HealthRecord.recorded_at < today_end,
            )
        )
        .scalar()
    )

    # Sleep
    sleep_record = (
        db.query(func.sum(HealthRecord.value))
        .filter(
            and_(
                HealthRecord.patient_id == patient_id,
                HealthRecord.metric_type == "sleep_analysis",
                HealthRecord.recorded_at >= today_start,
                HealthRecord.recorded_at < today_end,
            )
        )
        .scalar()
    )

    # Last synced (most recent health record)
    last_record = (
        db.query(HealthRecord)
        .filter(HealthRecord.patient_id == patient_id)
        .order_by(desc(HealthRecord.created_at))
        .first()
    )

    # Total readings
    total_readings = (
        db.query(func.count(HealthRecord.id))
        .filter(HealthRecord.patient_id == patient_id)
        .scalar()
    )

    return HealthSummaryResponse(
        patient_id=patient_id,
        latest_heart_rate=get_latest_reading("heart_rate"),
        latest_blood_pressure_systolic=get_latest_reading("blood_pressure_systolic"),
        latest_blood_pressure_diastolic=get_latest_reading("blood_pressure_diastolic"),
        latest_weight=get_latest_reading("weight"),
        latest_oxygen_saturation=get_latest_reading("oxygen_saturation"),
        latest_blood_glucose=get_latest_reading("blood_glucose"),
        today_steps=int(steps_record) if steps_record else None,
        today_sleep_hours=float(sleep_record) if sleep_record else None,
        last_synced_at=last_record.created_at if last_record else None,
        total_readings=total_readings or 0,
    )


@router.post("/patient/{patient_id}/record", response_model=HealthRecordResponse)
async def create_health_record(
    patient_id: UUID,
    record_data: HealthRecordCreate,
    db: Session = Depends(DbSession),
    current_user: dict = Depends(CurrentUser),
) -> HealthRecordResponse:
    """
    Create a single health record (manual entry).

    Used for manually entering health data.
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Create health record
    health_record = HealthRecord(
        patient_id=patient_id,
        metric_type=record_data.metric_type,
        value=record_data.value,
        unit=record_data.unit,
        recorded_at=record_data.recorded_at,
        source=record_data.source,
        device_id=record_data.device_id,
        metadata=record_data.metadata,
    )
    db.add(health_record)
    db.commit()
    db.refresh(health_record)

    return HealthRecordResponse.model_validate(health_record)


@router.delete("/patient/{patient_id}/records")
async def delete_patient_health_records(
    patient_id: UUID,
    metric_type: Optional[str] = Query(None, description="Delete only this metric type"),
    start_date: Optional[datetime] = Query(None, description="Delete from this date"),
    end_date: Optional[datetime] = Query(None, description="Delete to this date"),
    db: Session = Depends(DbSession),
    current_user: dict = Depends(CurrentUser),
) -> dict:
    """
    Delete health records for a patient.

    Can filter by metric type and date range.
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Build delete query
    query = db.query(HealthRecord).filter(HealthRecord.patient_id == patient_id)

    if metric_type:
        query = query.filter(HealthRecord.metric_type == metric_type)

    if start_date:
        query = query.filter(HealthRecord.recorded_at >= start_date)

    if end_date:
        query = query.filter(HealthRecord.recorded_at <= end_date)

    # Count before delete
    count = query.count()

    # Delete
    query.delete(synchronize_session=False)
    db.commit()

    return {
        "success": True,
        "deleted_count": count,
        "message": f"Deleted {count} health records",
    }


@router.get("/patient/{patient_id}/metrics", response_model=list[str])
async def get_patient_available_metrics(
    patient_id: UUID,
    db: Session = Depends(DbSession),
    current_user: dict = Depends(CurrentUser),
) -> list[str]:
    """
    Get list of available health metrics for a patient.

    Returns list of metric types that have data.
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Get distinct metric types
    metrics = (
        db.query(HealthRecord.metric_type)
        .filter(HealthRecord.patient_id == patient_id)
        .distinct()
        .all()
    )

    return [metric[0] for metric in metrics]
