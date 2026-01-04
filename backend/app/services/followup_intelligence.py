"""
Follow-up Intelligence Service.

Phase 16c: Proactive Intelligence

Generates smart follow-up reminders based on procedure type and specialty.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import FollowupSchedule, InsightPriority
from app.models.procedure import Procedure
from app.schemas.insights import FollowupReminder, SuggestedFollowup

logger = logging.getLogger(__name__)


# Procedure-specific follow-up rules
FOLLOWUP_RULES = {
    "cardiology": {
        "Stent Placement": [
            {"days": 7, "reason": "Post-stent check", "priority": 5},
            {"days": 30, "reason": "Monthly follow-up", "priority": 4},
            {"days": 180, "reason": "6-month angiogram review", "priority": 3},
        ],
        "Angioplasty (PTCA)": [
            {"days": 7, "reason": "Post-PTCA review", "priority": 5},
            {"days": 90, "reason": "3-month stress test", "priority": 3},
        ],
        "Pacemaker Implantation": [
            {"days": 1, "reason": "Day-1 device check", "priority": 5},
            {"days": 7, "reason": "1-week wound check", "priority": 4},
            {"days": 90, "reason": "3-month device interrogation", "priority": 3},
            {"days": 180, "reason": "6-month device check", "priority": 3},
        ],
        "Echocardiogram": [
            # Only if EF < 40% or other abnormality
            {
                "days": 180,
                "reason": "Repeat echo for monitoring",
                "priority": 3,
                "condition": "abnormal_findings",
            },
        ],
        "Coronary Angiography": [
            {"days": 7, "reason": "Post-cath site review", "priority": 4},
        ],
    },
    "ophthalmology": {
        "Cataract Surgery": [
            {"days": 1, "reason": "Day-1 post-op check", "priority": 5},
            {"days": 7, "reason": "1-week post-op review", "priority": 4},
            {"days": 30, "reason": "1-month final assessment", "priority": 3},
        ],
        "Intravitreal Injection": [
            {"days": 28, "reason": "Monthly injection", "priority": 4},
        ],
        "LASIK": [
            {"days": 1, "reason": "Day-1 post-op", "priority": 5},
            {"days": 7, "reason": "1-week check", "priority": 4},
            {"days": 90, "reason": "3-month final check", "priority": 2},
        ],
        "Glaucoma Surgery": [
            {"days": 1, "reason": "Day-1 IOP check", "priority": 5},
            {"days": 7, "reason": "1-week follow-up", "priority": 4},
            {"days": 30, "reason": "1-month review", "priority": 3},
        ],
    },
    "orthopedics": {
        "Total Knee Replacement": [
            {"days": 14, "reason": "Suture removal", "priority": 5},
            {"days": 42, "reason": "6-week X-ray", "priority": 4},
            {"days": 90, "reason": "3-month review", "priority": 3},
            {"days": 365, "reason": "1-year assessment", "priority": 2},
        ],
        "Total Hip Replacement": [
            {"days": 14, "reason": "Suture removal", "priority": 5},
            {"days": 42, "reason": "6-week X-ray", "priority": 4},
            {"days": 90, "reason": "3-month review", "priority": 3},
        ],
        "ACL Reconstruction": [
            {"days": 7, "reason": "Post-op wound check", "priority": 4},
            {"days": 42, "reason": "6-week physio review", "priority": 3},
            {"days": 90, "reason": "3-month strength test", "priority": 3},
            {"days": 180, "reason": "6-month return-to-sport assessment", "priority": 2},
        ],
        "Fracture Fixation": [
            {"days": 14, "reason": "Wound check", "priority": 4},
            {"days": 42, "reason": "6-week X-ray", "priority": 4},
            {"days": 90, "reason": "3-month X-ray (union check)", "priority": 3},
        ],
    },
    "gastroenterology": {
        "Colonoscopy": [
            # Only if polyps found
            {
                "days": 365,
                "reason": "1-year surveillance colonoscopy",
                "priority": 3,
                "condition": "polyps_found",
            },
        ],
        "ERCP": [
            {"days": 7, "reason": "Post-ERCP review", "priority": 4},
        ],
        "Upper GI Endoscopy": [
            {
                "days": 90,
                "reason": "3-month repeat endoscopy",
                "priority": 3,
                "condition": "biopsy_taken",
            },
        ],
    },
    "dermatology": {
        "Skin Biopsy": [
            {"days": 7, "reason": "Results discussion", "priority": 4},
        ],
        "Mohs Surgery": [
            {"days": 7, "reason": "Wound check", "priority": 4},
            {"days": 90, "reason": "3-month scar assessment", "priority": 2},
        ],
    },
}


class FollowupIntelligence:
    """
    Intelligence engine for procedure follow-ups.

    Automatically generates follow-up schedules based on:
    - Procedure type
    - Medical specialty
    - Clinical findings
    - Best practices
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def suggest_followups_after_procedure(
        self, procedure: Procedure
    ) -> list[SuggestedFollowup]:
        """
        Suggest follow-ups based on procedure type.

        Args:
            procedure: The completed procedure

        Returns:
            List of suggested follow-ups
        """
        category = procedure.category.lower()
        procedure_type = procedure.procedure_type

        # Get rules for this specialty
        specialty_rules = FOLLOWUP_RULES.get(category, {})
        procedure_rules = specialty_rules.get(procedure_type, [])

        suggestions = []

        for rule in procedure_rules:
            # Check if there's a condition
            if "condition" in rule:
                if not self._check_condition(rule["condition"], procedure):
                    continue

            suggestions.append(
                SuggestedFollowup(
                    days_from_procedure=rule["days"],
                    reason=rule["reason"],
                    priority=rule["priority"],
                    condition=rule.get("condition"),
                )
            )

        return suggestions

    async def create_followup_schedules(
        self,
        procedure: Procedure,
        suggestions: Optional[list[SuggestedFollowup]] = None,
    ) -> list[FollowupSchedule]:
        """
        Create follow-up schedules in the database.

        Args:
            procedure: The procedure
            suggestions: Optional list of suggestions (will generate if not provided)

        Returns:
            List of created follow-up schedules
        """
        if suggestions is None:
            suggestions = await self.suggest_followups_after_procedure(procedure)

        schedules = []

        for suggestion in suggestions:
            due_date = procedure.performed_at + timedelta(days=suggestion.days_from_procedure)

            schedule = FollowupSchedule(
                clinic_id=procedure.clinic_id,
                patient_id=procedure.patient_id,
                doctor_id=procedure.doctor_id,
                procedure_id=procedure.id,
                due_date=due_date,
                reason=suggestion.reason,
                priority=suggestion.priority,
            )

            self.db.add(schedule)
            schedules.append(schedule)

        await self.db.commit()

        logger.info(
            f"Created {len(schedules)} follow-up schedules for procedure {procedure.id}"
        )

        return schedules

    async def get_pending_followups(
        self,
        clinic_id: UUID,
        doctor_id: Optional[UUID] = None,
        days_ahead: int = 7,
    ) -> list[FollowupReminder]:
        """
        Get pending follow-ups due within specified days.

        Args:
            clinic_id: Clinic ID
            doctor_id: Optional doctor filter
            days_ahead: Look ahead this many days (default: 7)

        Returns:
            List of follow-up reminders
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)

        # Build query
        stmt = (
            select(FollowupSchedule)
            .where(
                FollowupSchedule.clinic_id == clinic_id,
                FollowupSchedule.completed == False,
                FollowupSchedule.due_date >= datetime.combine(today, datetime.min.time()),
                FollowupSchedule.due_date <= datetime.combine(end_date, datetime.max.time()),
            )
            .order_by(FollowupSchedule.due_date, FollowupSchedule.priority.desc())
        )

        if doctor_id:
            stmt = stmt.where(FollowupSchedule.doctor_id == doctor_id)

        result = await self.db.execute(stmt)
        schedules = result.scalars().all()

        # Convert to reminders with patient/procedure info
        reminders = []
        for schedule in schedules:
            # Load relationships
            await self.db.refresh(schedule, ["patient", "procedure"])

            days_overdue = (today - schedule.due_date.date()).days

            reminders.append(
                FollowupReminder(
                    patient_id=schedule.patient_id,
                    patient_name=schedule.patient.full_name,
                    procedure_type=schedule.procedure.procedure_type,
                    procedure_date=schedule.procedure.performed_at,
                    due_date=schedule.due_date,
                    reason=schedule.reason,
                    priority=schedule.priority,
                    days_overdue=max(0, days_overdue),
                )
            )

        return reminders

    async def get_overdue_followups(
        self,
        clinic_id: UUID,
        doctor_id: Optional[UUID] = None,
    ) -> list[FollowupReminder]:
        """
        Get overdue follow-ups.

        Args:
            clinic_id: Clinic ID
            doctor_id: Optional doctor filter

        Returns:
            List of overdue follow-up reminders
        """
        today = datetime.now().date()

        # Build query
        stmt = (
            select(FollowupSchedule)
            .where(
                FollowupSchedule.clinic_id == clinic_id,
                FollowupSchedule.completed == False,
                FollowupSchedule.due_date < datetime.combine(today, datetime.min.time()),
            )
            .order_by(FollowupSchedule.due_date, FollowupSchedule.priority.desc())
        )

        if doctor_id:
            stmt = stmt.where(FollowupSchedule.doctor_id == doctor_id)

        result = await self.db.execute(stmt)
        schedules = result.scalars().all()

        # Convert to reminders
        reminders = []
        for schedule in schedules:
            await self.db.refresh(schedule, ["patient", "procedure"])

            days_overdue = (today - schedule.due_date.date()).days

            reminders.append(
                FollowupReminder(
                    patient_id=schedule.patient_id,
                    patient_name=schedule.patient.full_name,
                    procedure_type=schedule.procedure.procedure_type,
                    procedure_date=schedule.procedure.performed_at,
                    due_date=schedule.due_date,
                    reason=schedule.reason,
                    priority=schedule.priority,
                    days_overdue=days_overdue,
                )
            )

        return reminders

    async def mark_followup_completed(
        self,
        followup_id: UUID,
        appointment_id: Optional[UUID] = None,
    ) -> FollowupSchedule:
        """
        Mark a follow-up as completed.

        Args:
            followup_id: Follow-up schedule ID
            appointment_id: Optional appointment ID if scheduled

        Returns:
            Updated follow-up schedule
        """
        stmt = select(FollowupSchedule).where(FollowupSchedule.id == followup_id)
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise ValueError(f"Follow-up schedule {followup_id} not found")

        schedule.completed = True
        schedule.completed_at = datetime.utcnow()
        schedule.scheduled_appointment_id = appointment_id

        await self.db.commit()
        await self.db.refresh(schedule)

        return schedule

    def _check_condition(self, condition: str, procedure: Procedure) -> bool:
        """
        Check if a follow-up condition is met.

        Args:
            condition: Condition string (e.g., "ef_below_40", "polyps_found")
            procedure: The procedure

        Returns:
            True if condition is met
        """
        # Check custom fields for conditions
        custom_fields = procedure.custom_fields or {}

        if condition == "ef_below_40":
            ef = custom_fields.get("ef_after") or custom_fields.get("ef")
            return ef is not None and ef < 40

        elif condition == "abnormal_findings":
            findings = (procedure.findings or "").lower()
            return any(
                word in findings
                for word in ["abnormal", "reduced", "impaired", "dysfunction"]
            )

        elif condition == "polyps_found":
            findings = (procedure.findings or "").lower()
            return "polyp" in findings

        elif condition == "biopsy_taken":
            findings = (procedure.findings or "").lower()
            return "biopsy" in findings

        # Default: condition not met
        return False
