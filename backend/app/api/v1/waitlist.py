"""
Waitlist Management API endpoints.

Manage patient queues when appointment slots are unavailable.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.models.waitlist import WaitlistPriority, WaitlistStatus, NotificationChannel
from app.services.waitlist import WaitlistService, get_waitlist_service

router = APIRouter()


class WaitlistCreateRequest(BaseModel):
    """Request to add to waitlist."""
    patient_name: str = Field(..., min_length=1, max_length=200)
    patient_phone: str = Field(..., min_length=10, max_length=20)
    preferred_date: date
    doctor_id: Optional[UUID] = None
    patient_id: Optional[UUID] = None
    alternate_date: Optional[date] = None
    preferred_time_slot: Optional[str] = None
    priority: WaitlistPriority = WaitlistPriority.NORMAL
    chief_complaint: Optional[str] = None
    is_emergency: bool = False
    notification_channel: NotificationChannel = NotificationChannel.SMS


class WaitlistEntryModel(BaseModel):
    """Waitlist entry response model."""
    id: str
    clinic_id: str
    doctor_id: Optional[str]
    patient_id: Optional[str]
    patient_name: str
    patient_phone: str
    preferred_date: date
    alternate_date: Optional[date]
    preferred_time_slot: Optional[str]
    priority: str
    status: str
    queue_position: int
    chief_complaint: Optional[str]
    is_emergency: bool
    notification_channel: str
    notification_count: int
    last_notified_at: Optional[datetime]
    offered_slot_time: Optional[datetime]
    created_at: datetime


class QueuePositionModel(BaseModel):
    """Queue position response."""
    entry_id: str
    position: int
    ahead_count: int
    estimated_wait_minutes: int
    priority: str
    status: str


class WaitlistStatsModel(BaseModel):
    """Waitlist statistics."""
    by_status: dict
    by_priority: dict
    waiting_count: int
    emergency_count: int
    booked_count: int


def entry_to_model(entry) -> WaitlistEntryModel:
    """Convert Waitlist to response model."""
    return WaitlistEntryModel(
        id=str(entry.id),
        clinic_id=str(entry.clinic_id),
        doctor_id=str(entry.doctor_id) if entry.doctor_id else None,
        patient_id=str(entry.patient_id) if entry.patient_id else None,
        patient_name=entry.patient_name,
        patient_phone=entry.patient_phone,
        preferred_date=entry.preferred_date,
        alternate_date=entry.alternate_date,
        preferred_time_slot=entry.preferred_time_slot,
        priority=entry.priority,
        status=entry.status,
        queue_position=entry.queue_position,
        chief_complaint=entry.chief_complaint,
        is_emergency=entry.is_emergency,
        notification_channel=entry.notification_channel,
        notification_count=entry.notification_count,
        last_notified_at=entry.last_notified_at,
        offered_slot_time=entry.offered_slot_time,
        created_at=entry.created_at,
    )


@router.post("/", response_model=WaitlistEntryModel, status_code=status.HTTP_201_CREATED)
async def add_to_waitlist(
    request: WaitlistCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Add a patient to the waitlist.

    Use when no appointment slots are available for the preferred date/doctor.
    The patient will be notified when a slot opens up.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_waitlist_service(db)
    entry = await service.add_to_waitlist(
        clinic_id=clinic_id,
        patient_name=request.patient_name,
        patient_phone=request.patient_phone,
        preferred_date=request.preferred_date,
        doctor_id=request.doctor_id,
        patient_id=request.patient_id,
        alternate_date=request.alternate_date,
        preferred_time_slot=request.preferred_time_slot,
        priority=request.priority,
        chief_complaint=request.chief_complaint,
        is_emergency=request.is_emergency,
        notification_channel=request.notification_channel,
    )

    return entry_to_model(entry)


@router.get("/", response_model=list[WaitlistEntryModel])
async def get_waitlist(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: Optional[UUID] = None,
    date_filter: Optional[date] = Query(None, alias="date"),
    status_filter: Optional[WaitlistStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get waitlist entries for the clinic.

    Filter by doctor, date, or status.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_waitlist_service(db)
    entries = await service.get_waitlist(
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        date_filter=date_filter,
        status=status_filter,
        limit=limit,
    )

    return [entry_to_model(e) for e in entries]


@router.get("/stats", response_model=WaitlistStatsModel)
async def get_waitlist_stats(
    db: DbSession,
    current_user: CurrentUser,
    date_filter: Optional[date] = Query(None, alias="date"),
):
    """Get waitlist statistics."""
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_waitlist_service(db)
    stats = await service.get_waitlist_stats(
        clinic_id=clinic_id,
        date_filter=date_filter,
    )

    return WaitlistStatsModel(**stats)


@router.get("/{entry_id}", response_model=WaitlistEntryModel)
async def get_waitlist_entry(
    entry_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a specific waitlist entry."""
    from app.models.waitlist import Waitlist

    entry = await db.get(Waitlist, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found",
        )

    if entry.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this entry",
        )

    return entry_to_model(entry)


@router.get("/{entry_id}/position", response_model=QueuePositionModel)
async def get_queue_position(
    entry_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get queue position and estimated wait time.

    Returns current position, number of people ahead, and estimated wait.
    """
    service = get_waitlist_service(db)
    position = await service.get_queue_position(entry_id)

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found",
        )

    return QueuePositionModel(**position)


@router.post("/{entry_id}/confirm", response_model=WaitlistEntryModel)
async def confirm_slot(
    entry_id: UUID,
    appointment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Confirm patient accepted the offered slot.

    Links the waitlist entry to the created appointment.
    """
    try:
        service = get_waitlist_service(db)
        entry = await service.confirm_slot(entry_id, appointment_id)
        return entry_to_model(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{entry_id}/decline", response_model=WaitlistEntryModel)
async def decline_slot(
    entry_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Patient declined the offered slot.

    Moves entry back to waiting status at end of queue.
    """
    try:
        service = get_waitlist_service(db)
        entry = await service.decline_slot(entry_id)
        return entry_to_model(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{entry_id}", response_model=WaitlistEntryModel)
async def cancel_entry(
    entry_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Cancel a waitlist entry."""
    try:
        service = get_waitlist_service(db)
        entry = await service.cancel_entry(entry_id)
        return entry_to_model(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/process-cancellation")
async def process_cancelled_appointment(
    doctor_id: UUID,
    slot_time: datetime,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Process a cancelled appointment slot.

    Finds the next waitlist patient and notifies them.
    Called when an appointment is cancelled.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_waitlist_service(db)
    entry = await service.process_cancelled_slot(
        doctor_id=doctor_id,
        slot_time=slot_time,
        clinic_id=clinic_id,
    )

    if entry:
        return {
            "message": "Waitlist patient notified",
            "entry_id": str(entry.id),
            "patient_name": entry.patient_name,
            "patient_phone": entry.patient_phone,
        }
    else:
        return {
            "message": "No waitlist patients for this slot",
        }


@router.post("/cleanup")
async def cleanup_expired_entries(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Clean up expired waitlist entries.

    Marks entries as expired if:
    - Preferred date is in the past
    - Slot offer expired without confirmation
    """
    if current_user.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can run cleanup",
        )

    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_waitlist_service(db)
    count = await service.cleanup_expired(clinic_id)

    return {
        "message": f"Cleaned up {count} expired entries",
        "expired_count": count,
    }
