"""
Slot Optimizer API endpoints.

AI-powered scheduling optimization endpoints for recommending
optimal appointment slots and analyzing schedule efficiency.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.doctor import Doctor
from app.schemas.slot_optimizer import (
    GapIdentificationResponse,
    OptimalSlot,
    ScheduleAnalysis,
    ScheduleAdjustment,
    ScheduleGap,
    ScheduleOptimizationSuggestions,
    SlotRecommendationRequest,
    SlotRecommendationResponse,
    UtilizationMetric,
    UtilizationMetrics,
)
from app.services.slot_optimizer import SlotOptimizerService, get_slot_optimizer_service

router = APIRouter()


@router.get("/optimal/{doctor_id}", response_model=SlotRecommendationResponse)
async def get_optimal_slots(
    doctor_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    date_from: date = Query(default_factory=date.today),
    date_to: date = Query(default_factory=lambda: date.today() + timedelta(days=7)),
    duration_minutes: int = Query(15, ge=5, le=120),
    appointment_type: str | None = None,
    patient_id: UUID | None = None,
    max_recommendations: int = Query(5, ge=1, le=20),
):
    """
    Get optimal available slots for a doctor.

    Returns AI-powered recommendations sorted by optimization score.
    Considers:
    - Gap minimization
    - Utilization improvement
    - Appointment type clustering
    - Doctor energy levels
    - Patient preferences

    Args:
        doctor_id: Doctor to find slots for
        date_from: Start of date range (default: today)
        date_to: End of date range (default: 7 days from today)
        duration_minutes: Appointment duration
        appointment_type: Type of appointment (for clustering)
        patient_id: Patient ID (for preference matching)
        max_recommendations: Number of recommendations (1-20)
    """
    # Verify clinic access
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get doctor and verify clinic
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    if doctor.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor does not belong to your clinic",
        )

    # Get optimal slots
    service = get_slot_optimizer_service(db)
    scored_slots = await service.get_optimal_slots(
        doctor_id=doctor_id,
        date_range_start=date_from,
        date_range_end=date_to,
        duration_minutes=duration_minutes,
        appointment_type=appointment_type,
        patient_id=patient_id,
        max_recommendations=max_recommendations,
    )

    # Calculate utilization metrics
    current_util_metrics = await service.get_utilization_metrics(
        doctor_id=doctor_id,
        date_range_start=date_from,
        date_range_end=date_to,
    )

    # Build response
    recommended_slots = [
        OptimalSlot(
            slot_time=slot.slot_time,
            score=round(slot.score, 2),
            reasons=slot.reasons,
            efficiency_impact=_get_efficiency_impact_description(slot.score),
            utilization_improvement=round(slot.utilization_bonus / 10, 2),
            gap_reduction=int((100 - slot.gap_penalty) / 10),
            nearby_appointment_types=slot.nearby_types,
        )
        for slot in scored_slots
    ]

    # Estimate potential utilization if one slot is booked
    potential_util = min(
        100,
        current_util_metrics.get("overall_utilization", 0) + 2.0,
    )

    return SlotRecommendationResponse(
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        date_range_start=date_from,
        date_range_end=date_to,
        recommended_slots=recommended_slots,
        current_utilization=current_util_metrics.get("overall_utilization", 0),
        potential_utilization=round(potential_util, 2),
    )


@router.post("/recommendations", response_model=SlotRecommendationResponse)
async def get_slot_recommendations(
    request: SlotRecommendationRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get slot recommendations with advanced filtering.

    Allows posting complex constraints and filters for slot recommendations.

    Request body:
        - doctor_id: Doctor to schedule with
        - date_range_start: Start date
        - date_range_end: End date
        - duration_minutes: Appointment duration
        - appointment_type: Type of appointment (optional)
        - patient_id: Patient for preference matching (optional)
        - max_recommendations: Number of slots to return
        - constraints: Additional constraints (e.g., preferred times)
    """
    # Verify clinic access
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get doctor
    result = await db.execute(select(Doctor).where(Doctor.id == request.doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor or doctor.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Get recommendations
    service = get_slot_optimizer_service(db)
    scored_slots = await service.get_optimal_slots(
        doctor_id=request.doctor_id,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end,
        duration_minutes=request.duration_minutes,
        appointment_type=request.appointment_type,
        patient_id=request.patient_id,
        max_recommendations=request.max_recommendations,
        constraints=request.constraints,
    )

    # Get utilization
    util_metrics = await service.get_utilization_metrics(
        doctor_id=request.doctor_id,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end,
    )

    recommended_slots = [
        OptimalSlot(
            slot_time=slot.slot_time,
            score=round(slot.score, 2),
            reasons=slot.reasons,
            efficiency_impact=_get_efficiency_impact_description(slot.score),
            utilization_improvement=round(slot.utilization_bonus / 10, 2),
            gap_reduction=int((100 - slot.gap_penalty) / 10),
            nearby_appointment_types=slot.nearby_types,
        )
        for slot in scored_slots
    ]

    return SlotRecommendationResponse(
        doctor_id=request.doctor_id,
        doctor_name=doctor.name,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end,
        recommended_slots=recommended_slots,
        current_utilization=util_metrics.get("overall_utilization", 0),
        potential_utilization=min(
            100,
            util_metrics.get("overall_utilization", 0) + 2.0,
        ),
    )


@router.post("/analyze-schedule", response_model=ScheduleAnalysis)
async def analyze_schedule(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: UUID,
    target_date: date = Query(default_factory=date.today),
):
    """
    Analyze current schedule efficiency for a specific date.

    Returns:
        - Utilization rate
        - Gap analysis
        - Efficiency score
        - Improvement suggestions
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get doctor
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor or doctor.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Analyze schedule
    service = get_slot_optimizer_service(db)
    analysis = await service.analyze_schedule(doctor_id, target_date)

    # Convert gaps to schema
    gaps = [
        ScheduleGap(
            gap_start=g["gap_start"],
            gap_end=g["gap_end"],
            duration_minutes=g["duration_minutes"],
            is_fillable=g["is_fillable"],
            reason=g["reason"],
            recommended_action=g["recommended_action"],
        )
        for g in analysis.get("gaps", [])
    ]

    return ScheduleAnalysis(
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        date=target_date,
        utilization_rate=analysis["utilization_rate"],
        gap_count=analysis["gap_count"],
        total_gap_minutes=analysis["total_gap_minutes"],
        longest_gap_minutes=analysis["longest_gap_minutes"],
        appointment_count=analysis["appointment_count"],
        working_hours=analysis["working_hours"],
        suggestions=analysis["suggestions"],
        efficiency_score=analysis["efficiency_score"],
        gaps=gaps,
    )


@router.get("/utilization/{doctor_id}", response_model=UtilizationMetrics)
async def get_utilization_metrics(
    doctor_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    date_to: date = Query(default_factory=date.today),
):
    """
    Get detailed utilization metrics for a doctor.

    Returns utilization breakdown by:
    - Hour of day
    - Day of week
    - Peak and low hours
    - Trends

    Args:
        doctor_id: Doctor to analyze
        date_from: Start of analysis period (default: 30 days ago)
        date_to: End of analysis period (default: today)
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get doctor
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor or doctor.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Get metrics
    service = get_slot_optimizer_service(db)
    metrics = await service.get_utilization_metrics(
        doctor_id=doctor_id,
        date_range_start=date_from,
        date_range_end=date_to,
    )

    # Convert to schema
    by_hour = [UtilizationMetric(**m) for m in metrics["by_hour"]]
    by_day = [UtilizationMetric(**m) for m in metrics["by_day"]]

    return UtilizationMetrics(
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        date_range_start=date_from,
        date_range_end=date_to,
        by_hour=by_hour,
        by_day=by_day,
        overall_utilization=metrics["overall_utilization"],
        peak_hours=metrics["peak_hours"],
        low_hours=metrics["low_hours"],
        trends=metrics["trends"],
    )


@router.get("/gaps/{doctor_id}", response_model=GapIdentificationResponse)
async def identify_schedule_gaps(
    doctor_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    target_date: date = Query(default_factory=date.today),
):
    """
    Identify gaps in a doctor's schedule for a specific date.

    Returns:
        - All gaps in the schedule
        - Which gaps can be filled
        - Recommendations for filling gaps
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get doctor
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor or doctor.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Analyze schedule
    service = get_slot_optimizer_service(db)
    analysis = await service.analyze_schedule(doctor_id, target_date)

    # Convert gaps
    gaps = [
        ScheduleGap(
            gap_start=g["gap_start"],
            gap_end=g["gap_end"],
            duration_minutes=g["duration_minutes"],
            is_fillable=g["is_fillable"],
            reason=g["reason"],
            recommended_action=g["recommended_action"],
        )
        for g in analysis.get("gaps", [])
    ]

    fillable_gaps = [g for g in gaps if g.is_fillable]

    # Generate recommendations
    recommendations = []
    if fillable_gaps:
        total_fillable_minutes = sum(g.duration_minutes for g in fillable_gaps)
        slot_duration = doctor.slot_duration or 15
        potential_appointments = total_fillable_minutes // slot_duration
        recommendations.append(
            f"You can schedule up to {potential_appointments} more appointments today"
        )
        recommendations.append(
            "Consider offering these slots to waitlisted patients"
        )
    else:
        recommendations.append("No fillable gaps detected - schedule is well-packed")

    return GapIdentificationResponse(
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        date=target_date,
        gaps=gaps,
        total_gap_minutes=analysis["total_gap_minutes"],
        fillable_gap_count=len(fillable_gaps),
        recommendations=recommendations,
    )


@router.post("/suggest-adjustments", response_model=ScheduleOptimizationSuggestions)
async def suggest_schedule_adjustments(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: UUID,
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    date_to: date = Query(default_factory=date.today),
):
    """
    Get schedule optimization suggestions.

    Analyzes historical data and suggests adjustments to:
    - Slot duration
    - Working hours
    - Capacity allocation
    - Break times

    Returns expected improvement for each suggestion.

    Args:
        doctor_id: Doctor to optimize for
        date_from: Analysis start date (default: 30 days ago)
        date_to: Analysis end date (default: today)
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Get doctor
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor or doctor.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Get suggestions
    service = get_slot_optimizer_service(db)
    suggestions = await service.suggest_schedule_adjustments(
        doctor_id=doctor_id,
        date_range_start=date_from,
        date_range_end=date_to,
    )

    # Convert to schema
    adjustments = [ScheduleAdjustment(**adj) for adj in suggestions["adjustments"]]

    return ScheduleOptimizationSuggestions(
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        current_efficiency_score=suggestions["current_efficiency_score"],
        potential_efficiency_score=suggestions["potential_efficiency_score"],
        adjustments=adjustments,
        summary=suggestions["summary"],
        estimated_impact=suggestions["estimated_impact"],
    )


def _get_efficiency_impact_description(score: float) -> str:
    """Get human-readable efficiency impact description."""
    if score >= 80:
        return "Excellent - Highly recommended for optimal efficiency"
    elif score >= 60:
        return "Good - Will improve schedule efficiency"
    elif score >= 40:
        return "Fair - Moderate impact on efficiency"
    else:
        return "Low - Consider other slots for better efficiency"
