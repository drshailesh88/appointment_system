"""
No-show prediction service using machine learning.

Features:
- Feature engineering from patient/appointment history
- ML model training and prediction
- Risk categorization and mitigation suggestions
- Model performance tracking
"""

import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.noshow_prediction import NoShowPrediction, RiskLevel
from app.models.patient import Patient

logger = logging.getLogger(__name__)


# Model version
MODEL_VERSION = "1.0.0"

# Model storage path
MODEL_DIR = Path(__file__).parent.parent.parent / "ml_models"
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / f"noshow_model_{MODEL_VERSION}.pkl"
SCALER_PATH = MODEL_DIR / f"noshow_scaler_{MODEL_VERSION}.pkl"


class NoShowPredictionService:
    """Service for predicting no-show likelihood using ML."""

    def __init__(self, db: AsyncSession):
        """Initialize the service."""
        self.db = db
        self.model: RandomForestClassifier | None = None
        self.scaler: StandardScaler | None = None
        self._load_model()

    def _load_model(self) -> None:
        """Load pre-trained model from disk."""
        try:
            if MODEL_PATH.exists() and SCALER_PATH.exists():
                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                with open(SCALER_PATH, "rb") as f:
                    self.scaler = pickle.load(f)
                logger.info(f"Loaded no-show prediction model v{MODEL_VERSION}")
            else:
                logger.warning("No pre-trained model found. Using heuristics until trained.")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None
            self.scaler = None

    def _save_model(self) -> None:
        """Save trained model to disk."""
        try:
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(self.model, f)
            with open(SCALER_PATH, "wb") as f:
                pickle.dump(self.scaler, f)
            logger.info(f"Saved no-show prediction model v{MODEL_VERSION}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")

    async def _get_patient_history(self, patient_id: str) -> dict[str, Any]:
        """Get patient appointment history for feature engineering."""
        # Count total appointments
        total_appts_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status.in_([
                    AppointmentStatus.COMPLETED.value,
                    AppointmentStatus.CANCELLED.value,
                    AppointmentStatus.NO_SHOW.value,
                ])
            )
        )
        total_result = await self.db.execute(total_appts_query)
        total_appointments = total_result.scalar() or 0

        # Count no-shows
        noshow_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status == AppointmentStatus.NO_SHOW.value,
            )
        )
        noshow_result = await self.db.execute(noshow_query)
        no_shows = noshow_result.scalar() or 0

        # Count cancellations
        cancel_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status == AppointmentStatus.CANCELLED.value,
            )
        )
        cancel_result = await self.db.execute(cancel_query)
        cancellations = cancel_result.scalar() or 0

        # Calculate rates
        no_show_rate = no_shows / total_appointments if total_appointments > 0 else 0.0
        cancellation_rate = cancellations / total_appointments if total_appointments > 0 else 0.0

        # Get last appointment date
        last_appt_query = (
            select(func.max(Appointment.scheduled_start))
            .where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.status == AppointmentStatus.COMPLETED.value,
                )
            )
        )
        last_appt_result = await self.db.execute(last_appt_query)
        last_appointment = last_appt_result.scalar()

        days_since_last = 0
        if last_appointment:
            days_since_last = (datetime.now() - last_appointment).days

        return {
            "total_appointments": total_appointments,
            "no_shows": no_shows,
            "cancellations": cancellations,
            "no_show_rate": no_show_rate,
            "cancellation_rate": cancellation_rate,
            "days_since_last_appointment": days_since_last,
            "is_new_patient": total_appointments == 0,
        }

    async def _extract_features(
        self,
        appointment: Appointment,
        patient: Patient,
    ) -> dict[str, Any]:
        """Extract features from appointment and patient data."""
        # Get patient history
        history = await self._get_patient_history(str(appointment.patient_id))

        # Calculate lead time (days between booking and appointment)
        lead_time_days = (appointment.scheduled_start - appointment.created_at).days

        # Day of week (0 = Monday, 6 = Sunday)
        day_of_week = appointment.scheduled_start.weekday()

        # Hour of day
        hour_of_day = appointment.scheduled_start.hour

        # Is weekend
        is_weekend = day_of_week >= 5

        # Is early morning (before 9 AM) or late evening (after 6 PM)
        is_edge_hours = hour_of_day < 9 or hour_of_day >= 18

        # Patient age
        age = patient.age or 30  # Default to 30 if unknown

        # Age group (young, adult, senior)
        age_group = 0 if age < 30 else (1 if age < 60 else 2)

        # Is first appointment
        is_first_appointment = appointment.appointment_type == "new_consultation"

        # Booking source risk (voice/web/app lower risk than walk-in/phone)
        booking_source_risk = {
            "app": 0,
            "web": 0,
            "voice_agent": 0,
            "whatsapp": 1,
            "phone": 2,
            "walk_in": 3,
        }.get(appointment.booking_source, 2)

        # Appointment type risk
        appointment_type_risk = {
            "emergency": 0,
            "procedure": 0,
            "teleconsultation": 1,
            "follow_up": 1,
            "new_consultation": 2,
        }.get(appointment.appointment_type, 1)

        return {
            # Patient history features
            "total_appointments": history["total_appointments"],
            "no_shows": history["no_shows"],
            "no_show_rate": history["no_show_rate"],
            "cancellation_rate": history["cancellation_rate"],
            "days_since_last_appointment": history["days_since_last_appointment"],
            "is_new_patient": int(history["is_new_patient"]),

            # Appointment timing features
            "lead_time_days": lead_time_days,
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "is_weekend": int(is_weekend),
            "is_edge_hours": int(is_edge_hours),

            # Patient demographics
            "age": age,
            "age_group": age_group,

            # Appointment characteristics
            "is_first_appointment": int(is_first_appointment),
            "booking_source_risk": booking_source_risk,
            "appointment_type_risk": appointment_type_risk,
            "duration_minutes": appointment.duration_minutes,
        }

    def _features_to_vector(self, features: dict[str, Any]) -> np.ndarray:
        """Convert feature dict to numpy array for model input."""
        # Define feature order (must match training)
        feature_order = [
            "total_appointments",
            "no_shows",
            "no_show_rate",
            "cancellation_rate",
            "days_since_last_appointment",
            "is_new_patient",
            "lead_time_days",
            "day_of_week",
            "hour_of_day",
            "is_weekend",
            "is_edge_hours",
            "age",
            "age_group",
            "is_first_appointment",
            "booking_source_risk",
            "appointment_type_risk",
            "duration_minutes",
        ]

        return np.array([[features[f] for f in feature_order]])

    def _predict_with_heuristics(self, features: dict[str, Any]) -> float:
        """Fallback prediction using rule-based heuristics when no model exists."""
        score = 0.0

        # Patient history (40% weight)
        if features["is_new_patient"]:
            score += 0.15  # New patients have moderate risk
        else:
            score += features["no_show_rate"] * 0.4

        # Lead time (20% weight)
        if features["lead_time_days"] < 1:
            score += 0.05  # Last minute bookings
        elif features["lead_time_days"] > 14:
            score += 0.15  # Too far in advance
        else:
            score += 0.02  # Sweet spot

        # Timing (20% weight)
        if features["is_weekend"]:
            score += 0.10
        if features["is_edge_hours"]:
            score += 0.08
        if features["day_of_week"] == 0:  # Monday
            score += 0.05

        # Booking source (10% weight)
        score += features["booking_source_risk"] * 0.025

        # Appointment type (10% weight)
        score += features["appointment_type_risk"] * 0.033

        # Cap at 1.0
        return min(score, 1.0)

    def _categorize_risk(self, probability: float) -> str:
        """Categorize probability into risk level."""
        if probability < 0.20:
            return RiskLevel.LOW.value
        elif probability < 0.50:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.HIGH.value

    def _generate_mitigation_actions(
        self,
        risk_level: str,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate recommended mitigation actions based on risk."""
        actions = []

        if risk_level == RiskLevel.HIGH.value:
            actions.append({
                "action": "confirmation_call",
                "description": "Make confirmation call 24 hours before appointment",
                "priority": "high",
            })
            actions.append({
                "action": "send_multiple_reminders",
                "description": "Send reminders at 48h, 24h, and 2h before appointment",
                "priority": "high",
            })
            if features["is_new_patient"]:
                actions.append({
                    "action": "welcome_call",
                    "description": "Make welcome call to explain clinic procedures",
                    "priority": "medium",
                })

        elif risk_level == RiskLevel.MEDIUM.value:
            actions.append({
                "action": "send_reminders",
                "description": "Send reminders at 24h and 2h before appointment",
                "priority": "medium",
            })
            actions.append({
                "action": "enable_easy_reschedule",
                "description": "Provide easy rescheduling options in reminder",
                "priority": "low",
            })

        else:  # Low risk
            actions.append({
                "action": "standard_reminder",
                "description": "Send standard reminder 24h before appointment",
                "priority": "low",
            })

        # Overbooking suggestion for high-risk slots
        overbooking_factor = 1.0
        if risk_level == RiskLevel.HIGH.value:
            overbooking_factor = 1.3  # Can overbook by 30%
        elif risk_level == RiskLevel.MEDIUM.value:
            overbooking_factor = 1.1  # Can overbook by 10%

        return {
            "actions": actions,
            "overbooking_factor": overbooking_factor,
            "recommended_reminder_count": len([a for a in actions if "reminder" in a["action"]]),
        }

    async def predict_no_show(
        self,
        appointment_id: str,
    ) -> NoShowPrediction:
        """
        Predict no-show likelihood for an appointment.

        Args:
            appointment_id: UUID of appointment

        Returns:
            NoShowPrediction object with probability and risk level
        """
        # Get appointment with patient
        query = (
            select(Appointment)
            .where(Appointment.id == appointment_id)
        )
        result = await self.db.execute(query)
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")

        # Get patient
        patient_query = select(Patient).where(Patient.id == appointment.patient_id)
        patient_result = await self.db.execute(patient_query)
        patient = patient_result.scalar_one_or_none()

        if not patient:
            raise ValueError(f"Patient {appointment.patient_id} not found")

        # Extract features
        features = await self._extract_features(appointment, patient)

        # Predict probability
        if self.model and self.scaler:
            # Use ML model
            feature_vector = self._features_to_vector(features)
            scaled_features = self.scaler.transform(feature_vector)
            probability = self.model.predict_proba(scaled_features)[0][1]
        else:
            # Use heuristics
            probability = self._predict_with_heuristics(features)

        # Categorize risk
        risk_level = self._categorize_risk(probability)

        # Generate mitigation actions
        mitigation_actions = self._generate_mitigation_actions(risk_level, features)

        # Check if prediction already exists
        existing_query = select(NoShowPrediction).where(
            NoShowPrediction.appointment_id == appointment_id
        )
        existing_result = await self.db.execute(existing_query)
        existing_prediction = existing_result.scalar_one_or_none()

        if existing_prediction:
            # Update existing prediction
            existing_prediction.probability = probability
            existing_prediction.risk_level = risk_level
            existing_prediction.features_used = features
            existing_prediction.model_version = MODEL_VERSION
            existing_prediction.predicted_at = datetime.now()
            existing_prediction.mitigation_actions = mitigation_actions
            await self.db.commit()
            await self.db.refresh(existing_prediction)
            return existing_prediction
        else:
            # Create new prediction
            prediction = NoShowPrediction(
                appointment_id=appointment_id,
                probability=probability,
                risk_level=risk_level,
                features_used=features,
                model_version=MODEL_VERSION,
                mitigation_actions=mitigation_actions,
            )

            self.db.add(prediction)
            await self.db.commit()
            await self.db.refresh(prediction)

            logger.info(
                f"Predicted no-show for appointment {appointment_id}: "
                f"{risk_level} risk ({int(probability * 100)}%)"
            )

            return prediction

    async def batch_predict(
        self,
        appointment_ids: list[str],
    ) -> list[NoShowPrediction]:
        """Predict no-show for multiple appointments."""
        predictions = []

        for appointment_id in appointment_ids:
            try:
                prediction = await self.predict_no_show(appointment_id)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Error predicting for {appointment_id}: {e}")

        return predictions

    async def get_high_risk_appointments(
        self,
        clinic_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[tuple[Appointment, NoShowPrediction]]:
        """Get all high-risk appointments for a clinic."""
        # Default to next 7 days
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        # Query appointments with predictions
        query = (
            select(Appointment, NoShowPrediction)
            .join(NoShowPrediction, Appointment.id == NoShowPrediction.appointment_id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(
                and_(
                    Patient.clinic_id == clinic_id,
                    Appointment.scheduled_start >= start_date,
                    Appointment.scheduled_start <= end_date,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED.value,
                        AppointmentStatus.CONFIRMED.value,
                    ]),
                    NoShowPrediction.risk_level == RiskLevel.HIGH.value,
                )
            )
            .order_by(NoShowPrediction.probability.desc())
        )

        result = await self.db.execute(query)
        return result.all()

    async def record_outcome(
        self,
        appointment_id: str,
        actual_status: str,
    ) -> None:
        """Record actual appointment outcome for model improvement."""
        query = select(NoShowPrediction).where(
            NoShowPrediction.appointment_id == appointment_id
        )
        result = await self.db.execute(query)
        prediction = result.scalar_one_or_none()

        if not prediction:
            logger.warning(f"No prediction found for appointment {appointment_id}")
            return

        # Determine if prediction was accurate
        was_no_show = actual_status == AppointmentStatus.NO_SHOW.value
        predicted_no_show = prediction.probability >= 0.5

        prediction.actual_outcome = actual_status
        prediction.was_accurate = was_no_show == predicted_no_show
        prediction.feedback_recorded_at = datetime.now()

        await self.db.commit()

        logger.info(
            f"Recorded outcome for {appointment_id}: "
            f"predicted={predicted_no_show}, actual={was_no_show}, "
            f"accurate={prediction.was_accurate}"
        )

    async def get_model_stats(self) -> dict[str, Any]:
        """Get model performance statistics."""
        # Count predictions with feedback
        total_query = select(func.count(NoShowPrediction.id)).where(
            NoShowPrediction.actual_outcome.isnot(None)
        )
        total_result = await self.db.execute(total_query)
        total_predictions = total_result.scalar() or 0

        # Count accurate predictions
        accurate_query = select(func.count(NoShowPrediction.id)).where(
            and_(
                NoShowPrediction.actual_outcome.isnot(None),
                NoShowPrediction.was_accurate == True,
            )
        )
        accurate_result = await self.db.execute(accurate_query)
        accurate_predictions = accurate_result.scalar() or 0

        # Calculate metrics
        accuracy = accurate_predictions / total_predictions if total_predictions > 0 else 0.0

        # Get risk level distribution
        risk_dist_query = (
            select(
                NoShowPrediction.risk_level,
                func.count(NoShowPrediction.id),
            )
            .group_by(NoShowPrediction.risk_level)
        )
        risk_dist_result = await self.db.execute(risk_dist_query)
        risk_distribution = dict(risk_dist_result.all())

        return {
            "model_version": MODEL_VERSION,
            "total_predictions": total_predictions,
            "accurate_predictions": accurate_predictions,
            "accuracy": round(accuracy, 4),
            "has_trained_model": self.model is not None,
            "risk_distribution": risk_distribution,
        }

    async def train_model(self, min_samples: int = 100) -> dict[str, Any]:
        """
        Train/retrain the ML model using historical data.

        Args:
            min_samples: Minimum number of samples needed for training

        Returns:
            Training statistics
        """
        logger.info("Starting model training...")

        # Get historical appointments with outcomes
        query = (
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(
                Appointment.status.in_([
                    AppointmentStatus.COMPLETED.value,
                    AppointmentStatus.NO_SHOW.value,
                ])
            )
        )
        result = await self.db.execute(query)
        appointments_with_patients = result.all()

        if len(appointments_with_patients) < min_samples:
            logger.warning(
                f"Not enough samples for training: {len(appointments_with_patients)} < {min_samples}"
            )
            return {
                "success": False,
                "message": f"Need at least {min_samples} completed appointments to train model",
                "samples_found": len(appointments_with_patients),
            }

        # Extract features and labels
        X_list = []
        y_list = []

        for appointment, patient in appointments_with_patients:
            features = await self._extract_features(appointment, patient)
            feature_vector = self._features_to_vector(features)
            X_list.append(feature_vector[0])

            # Label: 1 if no-show, 0 otherwise
            y_list.append(1 if appointment.status == AppointmentStatus.NO_SHOW.value else 0)

        X = np.array(X_list)
        y = np.array(y_list)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model (Random Forest for better performance)
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            class_weight="balanced",  # Handle imbalanced data
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)

        # Save model
        self._save_model()

        stats = {
            "success": True,
            "model_version": MODEL_VERSION,
            "total_samples": len(X),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "train_accuracy": round(train_score, 4),
            "test_accuracy": round(test_score, 4),
            "no_show_rate": round(y.mean(), 4),
        }

        logger.info(f"Model training completed: {stats}")
        return stats


def get_noshow_prediction_service(db: AsyncSession) -> NoShowPredictionService:
    """Dependency to get NoShowPredictionService."""
    return NoShowPredictionService(db)
