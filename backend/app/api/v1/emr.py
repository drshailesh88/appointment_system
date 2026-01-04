"""
EMR Integration API Endpoints.

Phase 13: Advanced EMR Integration
Provides real-time sync between Practice Manager and DocAssist EMR.
"""

import logging
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.procedure import Procedure
from app.schemas.emr import (
    EMRPatientResponse,
    EMRPrescriptionSummary,
    EMRSyncStatusResponse,
    EMRSyncTriggerResponse,
    EMRVisitResponse,
    PatientTimelineRequest,
    PatientTimelineResponse,
    TimelineEvent,
    TimelineEventSource,
    TimelineEventType,
)
from app.services.emr_sync_service import get_emr_sync_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/status",
    response_model=EMRSyncStatusResponse,
    summary="Get EMR sync status",
    description="Returns current sync status, last sync time, and statistics",
)
async def get_emr_sync_status():
    """Get EMR synchronization status."""
    emr_service = get_emr_sync_service()
    status_data = emr_service.get_status()

    return EMRSyncStatusResponse(**status_data)


@router.post(
    "/sync",
    response_model=EMRSyncTriggerResponse,
    summary="Trigger manual sync",
    description="Manually trigger a full sync with EMR database",
)
async def trigger_manual_sync(db: AsyncSession = Depends(get_db)):
    """Trigger a manual sync with EMR."""
    emr_service = get_emr_sync_service()

    if not emr_service.is_available():
        return EMRSyncTriggerResponse(
            message="EMR sync not available",
            error="EMR database not found or sync disabled",
        )

    logger.info("Manual EMR sync triggered")
    stats = await emr_service.full_sync(db)

    if "error" in stats:
        return EMRSyncTriggerResponse(
            message="Sync failed",
            error=stats["error"],
            stats=stats,
        )

    return EMRSyncTriggerResponse(
        message="Sync completed successfully",
        stats=stats,
    )


@router.get(
    "/patients/{patient_id}",
    response_model=EMRPatientResponse,
    summary="Get patient from EMR",
    description="Fetch patient details directly from EMR database",
)
async def get_emr_patient(patient_id: str):
    """Get patient details from EMR."""
    emr_service = get_emr_sync_service()

    if not emr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EMR integration not available",
        )

    patient = await emr_service.emr_async.get_patient(patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found in EMR",
        )

    return EMRPatientResponse(
        id=patient.id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        phone=patient.phone,
        email=patient.email,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender,
        blood_group=patient.blood_group,
        allergies=patient.allergies,
        address=patient.address,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


@router.get(
    "/patients/{patient_id}/visits",
    response_model=List[EMRVisitResponse],
    summary="Get patient visit history",
    description="Retrieve visit/consultation history from EMR for a patient",
)
async def get_patient_visits(
    patient_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get visit history for a patient from EMR."""
    emr_service = get_emr_sync_service()

    if not emr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EMR integration not available",
        )

    # Get patient to find EMR ID
    stmt = select(Patient).where(
        or_(
            Patient.id == patient_id,
            Patient.emr_patient_id == patient_id,
        )
    )
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    emr_patient_id = patient.emr_patient_id or patient_id

    # Fetch visits from EMR
    visits = await emr_service.emr_async.get_patient_visits(emr_patient_id, limit)

    return [
        EMRVisitResponse(
            id=visit.id,
            patient_id=visit.patient_id,
            doctor_name=visit.doctor_name,
            visit_date=visit.visit_date,
            chief_complaint=visit.chief_complaint,
            diagnosis=visit.diagnosis,
            notes=visit.notes,
            vitals=visit.vitals,
            prescriptions=visit.prescriptions,
            created_at=visit.created_at,
        )
        for visit in visits
    ]


@router.get(
    "/patients/{patient_id}/prescriptions",
    response_model=List[EMRPrescriptionSummary],
    summary="Get patient prescription history",
    description="Retrieve prescription summaries from EMR visits",
)
async def get_patient_prescriptions(
    patient_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get prescription history for a patient from EMR."""
    # Use the visits endpoint and extract prescriptions
    visits = await get_patient_visits(patient_id, limit, db)

    prescriptions = []
    for visit in visits:
        if visit.prescriptions:
            prescriptions.append(
                EMRPrescriptionSummary(
                    visit_id=visit.id,
                    visit_date=visit.visit_date,
                    doctor_name=visit.doctor_name,
                    medications=visit.prescriptions,
                    instructions=visit.notes,
                )
            )

    return prescriptions


@router.get(
    "/patients/{patient_id}/timeline",
    response_model=PatientTimelineResponse,
    summary="Get patient timeline",
    description="Get unified timeline of appointments, visits, and procedures",
)
async def get_patient_timeline(
    patient_id: UUID,
    limit: int = 50,
    include_appointments: bool = True,
    include_visits: bool = True,
    include_procedures: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Get unified patient timeline combining:
    - Appointments (Practice Manager)
    - Visits (EMR)
    - Procedures (Practice Manager)
    """
    emr_service = get_emr_sync_service()

    # Get patient
    stmt = select(Patient).where(Patient.id == patient_id)
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    timeline_events: List[TimelineEvent] = []

    # 1. Get appointments from Practice Manager
    if include_appointments:
        stmt = (
            select(Appointment)
            .options(selectinload(Appointment.doctor))
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.scheduled_start.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        appointments = result.scalars().all()

        for apt in appointments:
            timeline_events.append(
                TimelineEvent(
                    event_type=TimelineEventType.APPOINTMENT,
                    timestamp=apt.scheduled_start,
                    title=f"{apt.appointment_type.replace('_', ' ').title()} - {apt.status.title()}",
                    description=apt.notes,
                    doctor_name=apt.doctor.name if apt.doctor else "Unknown",
                    source=TimelineEventSource.PRACTICE_MANAGER,
                    status=apt.status,
                    chief_complaint=apt.chief_complaint,
                    appointment_id=str(apt.id),
                )
            )

    # 2. Get visits from EMR
    if include_visits and emr_service.is_available() and patient.emr_patient_id:
        try:
            visits = await emr_service.emr_async.get_patient_visits(
                patient.emr_patient_id,
                limit=limit,
            )

            for visit in visits:
                timeline_events.append(
                    TimelineEvent(
                        event_type=TimelineEventType.VISIT,
                        timestamp=datetime.fromisoformat(visit.visit_date),
                        title=f"Consultation - {visit.doctor_name}",
                        description=visit.notes,
                        doctor_name=visit.doctor_name,
                        source=TimelineEventSource.EMR,
                        chief_complaint=visit.chief_complaint,
                        diagnosis=visit.diagnosis,
                        visit_id=visit.id,
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching EMR visits: {e}")

    # 3. Get procedures from Practice Manager
    if include_procedures:
        stmt = (
            select(Procedure)
            .options(selectinload(Procedure.doctor))
            .where(Procedure.patient_id == patient_id)
            .order_by(Procedure.performed_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        procedures = result.scalars().all()

        for proc in procedures:
            timeline_events.append(
                TimelineEvent(
                    event_type=TimelineEventType.PROCEDURE,
                    timestamp=proc.performed_at,
                    title=f"{proc.procedure_type}: {proc.name}",
                    description=proc.description,
                    doctor_name=proc.doctor.name if proc.doctor else "Unknown",
                    source=TimelineEventSource.PRACTICE_MANAGER,
                    outcome=proc.outcome,
                    findings=proc.findings,
                    notes=proc.notes,
                    procedure_id=str(proc.id),
                )
            )

    # Sort all events by timestamp (most recent first)
    timeline_events.sort(key=lambda x: x.timestamp, reverse=True)

    # Limit total events
    timeline_events = timeline_events[:limit]

    return PatientTimelineResponse(
        patient_id=str(patient_id),
        patient_name=patient.full_name,
        total_events=len(timeline_events),
        events=timeline_events,
        emr_available=emr_service.is_available(),
    )


@router.post(
    "/appointments/{appointment_id}/link-visit/{visit_id}",
    summary="Link appointment to EMR visit",
    description="Link a completed appointment to its corresponding EMR visit",
)
async def link_appointment_to_visit(
    appointment_id: UUID,
    visit_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Link an appointment to its EMR visit after consultation."""
    emr_service = get_emr_sync_service()

    if not emr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EMR integration not available",
        )

    success = await emr_service.link_appointment_to_visit(
        str(appointment_id),
        visit_id,
        db,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to link appointment to visit",
        )

    return {
        "message": "Appointment successfully linked to visit",
        "appointment_id": str(appointment_id),
        "visit_id": visit_id,
    }
