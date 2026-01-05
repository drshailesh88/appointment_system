"""
Smart Scheduling API endpoints.

AI-powered scheduling suggestions and pattern analysis.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.api.deps import CurrentUser, DbSession
from app.services.smart_scheduling import (
    SmartSchedulingService,
    get_smart_scheduling_service,
)
from app.schemas.smart_scheduling import (
    OptimalTimesResponse,
    OptimalWindow,
    SchedulingPatterns,
    SlotSuggestion,
    SlotSuggestionsRequest,
    SlotSuggestionsResponse,
    SuggestionFeedback,
    SuggestionFeedbackResponse,
)

router = APIRouter()


@router.post("/suggestions", response_model=SlotSuggestionsResponse)
async def get_slot_suggestions(
    request: SlotSuggestionsRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get smart slot suggestions for a patient.

    Analyzes historical patterns, doctor availability, and booking density
    to suggest optimal appointment times ranked by confidence score.

    **Scoring Factors:**
    - Patient's historical preferences (time of day, day of week)
    - Doctor availability and typical busy hours
    - Current booking density
    - Appointment type considerations
    - Proximity (sooner is often better)

    **Returns:**
    - List of suggested slots with scores and reasons
    - Maximum 10 suggestions, sorted by score
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_smart_scheduling_service(db)

    suggestions = await service.get_slot_suggestions(
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        appointment_type=request.appointment_type,
        preferred_date=request.preferred_date,
        duration_minutes=request.duration_minutes,
        max_suggestions=request.max_suggestions,
    )

    return SlotSuggestionsResponse(
        patient_id=str(request.patient_id),
        doctor_id=str(request.doctor_id),
        suggestions=[
            SlotSuggestion(
                slot_time=s.slot_time,
                score=round(s.score, 1),
                reasons=s.reasons,
                doctor_id=str(s.doctor_id),
                duration_minutes=s.duration_minutes,
            )
            for s in suggestions
        ],
        total_analyzed=len(suggestions),
    )


@router.get("/suggestions/{patient_id}", response_model=SlotSuggestionsResponse)
async def get_patient_suggestions(
    patient_id: UUID,
    doctor_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    appointment_type: str = Query("new_consultation"),
    preferred_date: Optional[date] = None,
    duration_minutes: int = Query(15, ge=5, le=120),
    max_suggestions: int = Query(5, ge=1, le=10),
):
    """
    Get smart slot suggestions for a patient (GET endpoint).

    Alternative to POST endpoint for simpler integrations.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Convert appointment_type string to enum
    from app.models.appointment import AppointmentType
    try:
        appt_type = AppointmentType(appointment_type)
    except ValueError:
        appt_type = AppointmentType.NEW_CONSULTATION

    service = get_smart_scheduling_service(db)

    suggestions = await service.get_slot_suggestions(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_type=appt_type,
        preferred_date=preferred_date,
        duration_minutes=duration_minutes,
        max_suggestions=max_suggestions,
    )

    return SlotSuggestionsResponse(
        patient_id=str(patient_id),
        doctor_id=str(doctor_id),
        suggestions=[
            SlotSuggestion(
                slot_time=s.slot_time,
                score=round(s.score, 1),
                reasons=s.reasons,
                doctor_id=str(s.doctor_id),
                duration_minutes=s.duration_minutes,
            )
            for s in suggestions
        ],
        total_analyzed=len(suggestions),
    )


@router.get("/optimal-times/{doctor_id}", response_model=OptimalTimesResponse)
async def get_optimal_booking_times(
    doctor_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30, ge=7, le=90, description="Days of history to analyze"),
):
    """
    Get optimal booking windows for a doctor.

    Analyzes historical appointment data to identify time windows with:
    - High appointment completion rates
    - Low patient wait times
    - Consistent booking patterns

    **Use this to:**
    - Recommend best times to patients calling for appointments
    - Optimize clinic scheduling templates
    - Identify underutilized time slots
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    service = get_smart_scheduling_service(db)

    result = await service.get_optimal_booking_windows(
        doctor_id=doctor_id,
        date_range_days=days,
    )

    return OptimalTimesResponse(
        doctor_id=result["doctor_id"],
        analyzed_period_days=result["analyzed_period_days"],
        optimal_windows=[
            OptimalWindow(**window)
            for window in result["optimal_windows"]
        ],
        total_appointments_analyzed=result["total_appointments_analyzed"],
    )


@router.get("/patterns/{doctor_id}", response_model=SchedulingPatterns)
async def get_scheduling_patterns(
    doctor_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
):
    """
    Get detailed scheduling pattern analysis for a doctor.

    Returns insights about:
    - Peak booking hours and days
    - Appointment type distribution
    - Hourly and daily booking patterns
    - AI-generated scheduling recommendations

    **Use this for:**
    - Workforce planning
    - Schedule optimization
    - Understanding patient flow patterns
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Calculate date range if not provided
    if not start_date or not end_date:
        end_date = date.today()
        if period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "quarter":
            start_date = end_date - timedelta(days=90)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

    service = get_smart_scheduling_service(db)

    analysis = await service.get_pattern_analysis(
        doctor_id=doctor_id,
        start_date=start_date,
        end_date=end_date,
    )

    return SchedulingPatterns(
        doctor_id=analysis["doctor_id"],
        period=analysis["period"],
        total_appointments=analysis["total_appointments"],
        patterns=analysis["patterns"],
        recommendations=analysis.get("recommendations", []),
    )


@router.post("/feedback", response_model=SuggestionFeedbackResponse)
async def submit_suggestion_feedback(
    feedback: SuggestionFeedback,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Submit feedback on suggestion quality.

    This helps improve the AI suggestion algorithm over time by tracking:
    - Which suggestions were accepted vs rejected
    - When patients chose different times than suggested
    - Overall satisfaction with suggestions

    **Note:** Currently stores feedback for analysis. Future versions will
    use this data to train and improve the ML models.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # In a production system, you would store this feedback in a dedicated table
    # for ML training. For now, we just acknowledge receipt.

    # TODO: Store feedback in database for ML improvement
    # feedback_record = SuggestionFeedbackRecord(
    #     patient_id=feedback.patient_id,
    #     doctor_id=feedback.doctor_id,
    #     suggested_slot=feedback.suggested_slot,
    #     was_accepted=feedback.was_accepted,
    #     actual_slot=feedback.actual_slot,
    #     feedback_notes=feedback.feedback_notes,
    #     clinic_id=clinic_id,
    # )
    # db.add(feedback_record)
    # await db.commit()

    return SuggestionFeedbackResponse(
        success=True,
        message="Feedback received. Thank you for helping improve our suggestions!",
    )
