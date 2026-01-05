"""
No-show prediction API endpoints.

Provides ML-powered predictions for appointment no-shows
with risk categorization and mitigation suggestions.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.schemas.noshow import (
    HighRiskAppointment,
    HighRiskAppointmentListResponse,
    ModelRetrainRequest,
    ModelRetrainResponse,
    ModelStats,
    NoShowBatchRequest,
    NoShowBatchResponse,
    NoShowFeedbackRequest,
    NoShowFeedbackResponse,
    NoShowPredictionResponse,
)
from app.services.noshow_prediction import (
    NoShowPredictionService,
    get_noshow_prediction_service,
)
from sqlalchemy import select

router = APIRouter()


@router.get("/predict/{appointment_id}", response_model=NoShowPredictionResponse)
async def predict_no_show(
    appointment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    service: NoShowPredictionService = Depends(get_noshow_prediction_service),
):
    """
    Predict no-show likelihood for a single appointment.

    Generates ML-powered prediction with:
    - No-show probability (0-1)
    - Risk level (low/medium/high)
    - Feature analysis
    - Mitigation action recommendations

    Returns:
        NoShowPrediction with probability, risk level, and suggested actions
    """
    try:
        prediction = await service.predict_no_show(str(appointment_id))

        return NoShowPredictionResponse(
            id=prediction.id,
            appointment_id=prediction.appointment_id,
            probability=prediction.probability,
            risk_level=prediction.risk_level,
            risk_percentage=prediction.risk_percentage,
            is_high_risk=prediction.is_high_risk,
            is_medium_risk=prediction.is_medium_risk,
            is_low_risk=prediction.is_low_risk,
            features_used=prediction.features_used,
            model_version=prediction.model_version,
            predicted_at=prediction.predicted_at,
            mitigation_actions=prediction.mitigation_actions,
            was_accurate=prediction.was_accurate,
            actual_outcome=prediction.actual_outcome,
            created_at=prediction.created_at,
            updated_at=prediction.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error predicting no-show: {str(e)}",
        )


@router.post("/batch-predict", response_model=NoShowBatchResponse)
async def batch_predict_no_show(
    request: NoShowBatchRequest,
    db: DbSession,
    current_user: CurrentUser,
    service: NoShowPredictionService = Depends(get_noshow_prediction_service),
):
    """
    Predict no-show likelihood for multiple appointments.

    Useful for:
    - Daily appointment review
    - Bulk risk assessment
    - Proactive reminder scheduling

    Args:
        request: List of appointment IDs (max 100)

    Returns:
        Batch prediction results with summary statistics
    """
    try:
        appointment_ids = [str(aid) for aid in request.appointment_ids]
        predictions = await service.batch_predict(appointment_ids)

        # Count risk levels
        high_risk = sum(1 for p in predictions if p.is_high_risk)
        medium_risk = sum(1 for p in predictions if p.is_medium_risk)
        low_risk = sum(1 for p in predictions if p.is_low_risk)

        return NoShowBatchResponse(
            predictions=[
                NoShowPredictionResponse(
                    id=p.id,
                    appointment_id=p.appointment_id,
                    probability=p.probability,
                    risk_level=p.risk_level,
                    risk_percentage=p.risk_percentage,
                    is_high_risk=p.is_high_risk,
                    is_medium_risk=p.is_medium_risk,
                    is_low_risk=p.is_low_risk,
                    features_used=p.features_used,
                    model_version=p.model_version,
                    predicted_at=p.predicted_at,
                    mitigation_actions=p.mitigation_actions,
                    was_accurate=p.was_accurate,
                    actual_outcome=p.actual_outcome,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
                for p in predictions
            ],
            total_count=len(predictions),
            high_risk_count=high_risk,
            medium_risk_count=medium_risk,
            low_risk_count=low_risk,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch prediction: {str(e)}",
        )


@router.get("/high-risk", response_model=HighRiskAppointmentListResponse)
async def get_high_risk_appointments(
    db: DbSession,
    current_user: CurrentUser,
    start_date: Optional[datetime] = Query(None, description="Start date (default: today)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: +7 days)"),
    service: NoShowPredictionService = Depends(get_noshow_prediction_service),
):
    """
    Get all high-risk appointments for the clinic.

    Lists appointments predicted to have high no-show risk,
    helping staff prioritize confirmation calls and reminders.

    Args:
        start_date: Start of date range (default: today)
        end_date: End of date range (default: 7 days from now)

    Returns:
        List of high-risk appointments with patient/doctor info
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a clinic",
        )

    # Default date range
    if not start_date:
        start_date = datetime.now()
    if not end_date:
        end_date = start_date + timedelta(days=7)

    try:
        high_risk_appts = await service.get_high_risk_appointments(
            str(clinic_id),
            start_date=start_date,
            end_date=end_date,
        )

        # Build response with patient/doctor names
        appointments = []
        for appointment, prediction in high_risk_appts:
            # Get patient name
            patient_query = select(Patient).where(Patient.id == appointment.patient_id)
            patient_result = await db.execute(patient_query)
            patient = patient_result.scalar_one_or_none()

            # Get doctor name
            doctor_query = select(Doctor).where(Doctor.id == appointment.doctor_id)
            doctor_result = await db.execute(doctor_query)
            doctor = doctor_result.scalar_one_or_none()

            appointments.append(
                HighRiskAppointment(
                    appointment_id=appointment.id,
                    patient_id=appointment.patient_id,
                    patient_name=patient.full_name if patient else "Unknown",
                    doctor_id=appointment.doctor_id,
                    doctor_name=doctor.name if doctor else "Unknown",
                    scheduled_start=appointment.scheduled_start,
                    probability=prediction.probability,
                    risk_percentage=prediction.risk_percentage,
                    mitigation_actions=prediction.mitigation_actions,
                )
            )

        return HighRiskAppointmentListResponse(
            appointments=appointments,
            total_count=len(appointments),
            date_range_start=start_date,
            date_range_end=end_date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching high-risk appointments: {str(e)}",
        )


@router.post("/feedback", response_model=NoShowFeedbackResponse)
async def submit_prediction_feedback(
    request: NoShowFeedbackRequest,
    db: DbSession,
    current_user: CurrentUser,
    service: NoShowPredictionService = Depends(get_noshow_prediction_service),
):
    """
    Submit actual appointment outcome for model improvement.

    Called after appointment is completed/missed to record
    whether the prediction was accurate. This feedback is
    used to retrain and improve the model over time.

    Args:
        request: Appointment ID and actual outcome status

    Returns:
        Feedback confirmation with accuracy indicator
    """
    try:
        await service.record_outcome(
            str(request.appointment_id),
            request.actual_status,
        )

        # Get updated prediction to check accuracy
        from app.models.noshow_prediction import NoShowPrediction
        query = select(NoShowPrediction).where(
            NoShowPrediction.appointment_id == request.appointment_id
        )
        result = await db.execute(query)
        prediction = result.scalar_one_or_none()

        return NoShowFeedbackResponse(
            success=True,
            message="Feedback recorded successfully",
            was_accurate=prediction.was_accurate if prediction else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording feedback: {str(e)}",
        )


@router.get("/model-stats", response_model=ModelStats)
async def get_model_statistics(
    db: DbSession,
    current_user: CurrentUser,
    service: NoShowPredictionService = Depends(get_noshow_prediction_service),
):
    """
    Get model performance statistics.

    Provides insights into:
    - Total predictions made
    - Accuracy metrics
    - Risk level distribution
    - Model training status

    Returns:
        Model performance statistics
    """
    try:
        stats = await service.get_model_stats()
        return ModelStats(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching model stats: {str(e)}",
        )


@router.post("/retrain", response_model=ModelRetrainResponse)
async def retrain_model(
    request: ModelRetrainRequest,
    db: DbSession,
    current_admin: CurrentAdmin,
    service: NoShowPredictionService = Depends(get_noshow_prediction_service),
):
    """
    Trigger model retraining (admin only).

    Retrains the ML model using all historical appointment data.
    Requires at least 100 completed appointments for training.

    This endpoint should be called:
    - Periodically (weekly/monthly)
    - After significant data accumulation
    - When model accuracy degrades

    Args:
        request: Training parameters (min samples)

    Returns:
        Training results with accuracy metrics
    """
    try:
        result = await service.train_model(min_samples=request.min_samples)

        return ModelRetrainResponse(
            success=result.get("success", False),
            message=result.get("message"),
            model_version=result.get("model_version"),
            total_samples=result.get("total_samples"),
            training_samples=result.get("training_samples"),
            test_samples=result.get("test_samples"),
            train_accuracy=result.get("train_accuracy"),
            test_accuracy=result.get("test_accuracy"),
            no_show_rate=result.get("no_show_rate"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retraining model: {str(e)}",
        )
