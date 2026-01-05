"""
Procedure & Intervention Tracking Service.

Phase 9: Business logic for flexible procedure tracking across all specialties.

Key Features:
- CRUD operations for procedures
- Analytics (count by type, trends, doctor stats)
- Consumables tracking
- Integration with appointments
- EMR sync support
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.procedure import (
    Procedure,
    ProcedureOutcome,
    ProcedureSeverity,
    PROCEDURE_TEMPLATES,
)
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.procedure import (
    ProcedureCreate,
    ProcedureUpdate,
    ProcedureStats,
    ProcedureTypeCount,
    DoctorProcedureStats,
    ProcedureTrend,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcedureFilter:
    """Filter options for querying procedures."""

    clinic_id: UUID
    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    category: Optional[str] = None
    procedure_type: Optional[str] = None
    outcome: Optional[ProcedureOutcome] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_billable: Optional[bool] = None


class ProcedureService:
    """
    Procedure tracking service.

    Provides CRUD operations and analytics for procedures across all specialties.
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    # ========== CRUD Operations ==========

    async def create(
        self,
        clinic_id: UUID,
        data: ProcedureCreate,
    ) -> Procedure:
        """
        Create a new procedure record.

        Args:
            clinic_id: Clinic performing the procedure
            data: Procedure creation data
        """
        procedure = Procedure(
            clinic_id=clinic_id,
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            appointment_id=data.appointment_id,
            category=data.category,
            procedure_type=data.procedure_type,
            sub_type=data.sub_type,
            name=data.name,
            description=data.description,
            performed_at=data.performed_at or datetime.utcnow(),
            duration_minutes=data.duration_minutes,
            outcome=data.outcome.value,
            severity=data.severity.value,
            findings=data.findings,
            notes=data.notes,
            complications=data.complications,
            consumables=data.consumables,
            custom_fields=data.custom_fields,
            billing_code=data.billing_code,
            cpt_code=data.cpt_code,
            icd_code=data.icd_code,
            is_billable=data.is_billable,
            billed_amount=data.billed_amount,
            location=data.location,
            assistant_doctors=data.assistant_doctors,
            requires_followup=data.requires_followup,
            followup_notes=data.followup_notes,
        )

        self.db.add(procedure)
        await self.db.commit()
        await self.db.refresh(procedure)

        logger.info(
            f"Created procedure {procedure.id}: {procedure.procedure_type} for patient {procedure.patient_id}"
        )

        return procedure

    async def get_by_id(
        self,
        procedure_id: UUID,
        clinic_id: UUID,
    ) -> Optional[Procedure]:
        """Get procedure by ID."""
        result = await self.db.execute(
            select(Procedure)
            .options(
                selectinload(Procedure.patient),
                selectinload(Procedure.doctor),
            )
            .where(
                and_(
                    Procedure.id == procedure_id,
                    Procedure.clinic_id == clinic_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        procedure_id: UUID,
        clinic_id: UUID,
        data: ProcedureUpdate,
    ) -> Optional[Procedure]:
        """Update a procedure."""
        procedure = await self.get_by_id(procedure_id, clinic_id)
        if not procedure:
            return None

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                if field == "outcome":
                    value = value.value
                elif field == "severity":
                    value = value.value
                setattr(procedure, field, value)

        await self.db.commit()
        await self.db.refresh(procedure)

        logger.info(f"Updated procedure {procedure_id}")

        return procedure

    async def delete(
        self,
        procedure_id: UUID,
        clinic_id: UUID,
    ) -> bool:
        """Delete a procedure (soft delete via is_active flag would be better in production)."""
        procedure = await self.get_by_id(procedure_id, clinic_id)
        if not procedure:
            return False

        await self.db.delete(procedure)
        await self.db.commit()

        logger.info(f"Deleted procedure {procedure_id}")

        return True

    async def list(
        self,
        filters: ProcedureFilter,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Procedure], int]:
        """
        List procedures with filters and pagination.

        Returns tuple of (procedures, total_count).
        """
        # Build query
        query = (
            select(Procedure)
            .options(
                selectinload(Procedure.patient),
                selectinload(Procedure.doctor),
            )
            .where(Procedure.clinic_id == filters.clinic_id)
        )

        # Apply filters
        if filters.patient_id:
            query = query.where(Procedure.patient_id == filters.patient_id)
        if filters.doctor_id:
            query = query.where(Procedure.doctor_id == filters.doctor_id)
        if filters.category:
            query = query.where(Procedure.category == filters.category)
        if filters.procedure_type:
            query = query.where(Procedure.procedure_type == filters.procedure_type)
        if filters.outcome:
            query = query.where(Procedure.outcome == filters.outcome.value)
        if filters.start_date:
            start_dt = datetime.combine(filters.start_date, datetime.min.time())
            query = query.where(Procedure.performed_at >= start_dt)
        if filters.end_date:
            end_dt = datetime.combine(filters.end_date, datetime.max.time())
            query = query.where(Procedure.performed_at <= end_dt)
        if filters.is_billable is not None:
            query = query.where(Procedure.is_billable == filters.is_billable)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.order_by(Procedure.performed_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        procedures = list(result.scalars().all())

        return procedures, total

    # ========== Patient Procedures ==========

    async def get_patient_procedures(
        self,
        patient_id: UUID,
        clinic_id: UUID,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> list[Procedure]:
        """Get all procedures for a patient."""
        filters = ProcedureFilter(
            clinic_id=clinic_id,
            patient_id=patient_id,
            category=category,
        )
        procedures, _ = await self.list(filters, limit=limit)
        return procedures

    async def get_patient_procedure_summary(
        self,
        patient_id: UUID,
        clinic_id: UUID,
    ) -> dict:
        """Get summary of all procedures for a patient."""
        result = await self.db.execute(
            select(
                func.count().label("total"),
                Procedure.category,
                Procedure.procedure_type,
            )
            .where(
                and_(
                    Procedure.patient_id == patient_id,
                    Procedure.clinic_id == clinic_id,
                )
            )
            .group_by(Procedure.category, Procedure.procedure_type)
        )
        rows = result.all()

        summary = {}
        for row in rows:
            if row.category not in summary:
                summary[row.category] = {}
            summary[row.category][row.procedure_type] = row.total

        return summary

    # ========== Analytics ==========

    async def get_stats(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        doctor_id: Optional[UUID] = None,
    ) -> ProcedureStats:
        """
        Get procedure statistics for a time period.

        This is the "How many echos this month?" query.
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        base_filter = and_(
            Procedure.clinic_id == clinic_id,
            Procedure.performed_at >= start_dt,
            Procedure.performed_at <= end_dt,
        )

        if doctor_id:
            base_filter = and_(base_filter, Procedure.doctor_id == doctor_id)

        # Total count
        total_result = await self.db.execute(
            select(func.count()).where(base_filter)
        )
        total = total_result.scalar() or 0

        # By category
        category_result = await self.db.execute(
            select(
                Procedure.category,
                func.count().label("count"),
            )
            .where(base_filter)
            .group_by(Procedure.category)
        )
        by_category = {row.category: row.count for row in category_result.all()}

        # By type
        type_result = await self.db.execute(
            select(
                Procedure.procedure_type,
                func.count().label("count"),
            )
            .where(base_filter)
            .group_by(Procedure.procedure_type)
        )
        by_type = {row.procedure_type: row.count for row in type_result.all()}

        # By outcome
        outcome_result = await self.db.execute(
            select(
                Procedure.outcome,
                func.count().label("count"),
            )
            .where(base_filter)
            .group_by(Procedure.outcome)
        )
        by_outcome = {row.outcome: row.count for row in outcome_result.all()}

        # By severity
        severity_result = await self.db.execute(
            select(
                Procedure.severity,
                func.count().label("count"),
            )
            .where(base_filter)
            .group_by(Procedure.severity)
        )
        by_severity = {row.severity: row.count for row in severity_result.all()}

        # Total billed
        billed_result = await self.db.execute(
            select(
                func.coalesce(func.sum(Procedure.billed_amount), 0).label("total"),
                func.avg(Procedure.duration_minutes).label("avg_duration"),
            )
            .where(base_filter)
        )
        billed_row = billed_result.one()

        return ProcedureStats(
            total=total,
            by_category=by_category,
            by_type=by_type,
            by_outcome=by_outcome,
            by_severity=by_severity,
            total_billed=float(billed_row.total or 0),
            average_duration_minutes=float(billed_row.avg_duration) if billed_row.avg_duration else None,
        )

    async def get_type_counts(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        category: Optional[str] = None,
    ) -> list[ProcedureTypeCount]:
        """
        Get procedure counts by type.

        Use case: "How many stents vs echos vs angioplasties?"
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        base_filter = and_(
            Procedure.clinic_id == clinic_id,
            Procedure.performed_at >= start_dt,
            Procedure.performed_at <= end_dt,
        )

        if category:
            base_filter = and_(base_filter, Procedure.category == category)

        result = await self.db.execute(
            select(
                Procedure.category,
                Procedure.procedure_type,
                func.count().label("count"),
                func.coalesce(func.sum(Procedure.billed_amount), 0).label("total_billed"),
            )
            .where(base_filter)
            .group_by(Procedure.category, Procedure.procedure_type)
            .order_by(func.count().desc())
        )

        return [
            ProcedureTypeCount(
                category=row.category,
                procedure_type=row.procedure_type,
                count=row.count,
                total_billed=float(row.total_billed),
            )
            for row in result.all()
        ]

    async def get_doctor_stats(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[DoctorProcedureStats]:
        """
        Get procedure statistics per doctor.

        Use case: "Which doctor does the most procedures?"
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        base_filter = and_(
            Procedure.clinic_id == clinic_id,
            Procedure.performed_at >= start_dt,
            Procedure.performed_at <= end_dt,
        )

        # Get doctors with their procedure counts
        result = await self.db.execute(
            select(
                Procedure.doctor_id,
                func.count().label("total"),
                func.coalesce(func.sum(Procedure.billed_amount), 0).label("billed"),
                func.sum(case((Procedure.outcome == ProcedureOutcome.SUCCESSFUL.value, 1), else_=0)).label("successful"),
            )
            .where(base_filter)
            .group_by(Procedure.doctor_id)
        )
        rows = result.all()

        # Get doctor names
        doctor_ids = [row.doctor_id for row in rows]
        doctors_result = await self.db.execute(
            select(Doctor.id, Doctor.name)
            .where(Doctor.id.in_(doctor_ids))
        )
        doctor_names = {row.id: row.name for row in doctors_result.all()}

        # Build response
        stats = []
        for row in rows:
            # Get category breakdown for this doctor
            category_result = await self.db.execute(
                select(
                    Procedure.category,
                    func.count().label("count"),
                )
                .where(
                    and_(
                        base_filter,
                        Procedure.doctor_id == row.doctor_id,
                    )
                )
                .group_by(Procedure.category)
            )
            by_category = {r.category: r.count for r in category_result.all()}

            stats.append(DoctorProcedureStats(
                doctor_id=row.doctor_id,
                doctor_name=doctor_names.get(row.doctor_id, "Unknown"),
                total_procedures=row.total,
                by_category=by_category,
                total_billed=float(row.billed),
                success_rate=(row.successful / row.total * 100) if row.total > 0 else 0.0,
            ))

        return sorted(stats, key=lambda x: x.total_procedures, reverse=True)

    async def get_daily_trend(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        category: Optional[str] = None,
    ) -> list[ProcedureTrend]:
        """
        Get day-by-day procedure trend.

        Use case: "Show me procedure trends for the month."
        """
        trends = []
        current = start_date

        while current <= end_date:
            next_day = current + timedelta(days=1)
            current_dt = datetime.combine(current, datetime.min.time())
            next_dt = datetime.combine(next_day, datetime.min.time())

            base_filter = and_(
                Procedure.clinic_id == clinic_id,
                Procedure.performed_at >= current_dt,
                Procedure.performed_at < next_dt,
            )

            if category:
                base_filter = and_(base_filter, Procedure.category == category)

            # Count and billed
            count_result = await self.db.execute(
                select(
                    func.count().label("count"),
                    func.coalesce(func.sum(Procedure.billed_amount), 0).label("billed"),
                )
                .where(base_filter)
            )
            count_row = count_result.one()

            # By category
            category_result = await self.db.execute(
                select(
                    Procedure.category,
                    func.count().label("count"),
                )
                .where(base_filter)
                .group_by(Procedure.category)
            )
            categories = {r.category: r.count for r in category_result.all()}

            trends.append(ProcedureTrend(
                date=current_dt,
                count=count_row.count or 0,
                categories=categories,
                total_billed=float(count_row.billed or 0),
            ))

            current = next_day

        return trends

    # ========== Consumables Tracking ==========

    async def get_consumables_usage(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        category: Optional[str] = None,
    ) -> dict:
        """
        Get consumables usage summary.

        Use case: "How many Xience stents did we use this month?"
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        base_filter = and_(
            Procedure.clinic_id == clinic_id,
            Procedure.performed_at >= start_dt,
            Procedure.performed_at <= end_dt,
            Procedure.consumables.isnot(None),
        )

        if category:
            base_filter = and_(base_filter, Procedure.category == category)

        result = await self.db.execute(
            select(Procedure.consumables, Procedure.procedure_type)
            .where(base_filter)
        )

        # Aggregate consumables
        usage = {}
        for row in result.all():
            if row.consumables:
                proc_type = row.procedure_type
                if proc_type not in usage:
                    usage[proc_type] = {}

                for key, value in row.consumables.items():
                    if key not in usage[proc_type]:
                        usage[proc_type][key] = {}

                    # Count by value
                    str_value = str(value)
                    if str_value not in usage[proc_type][key]:
                        usage[proc_type][key][str_value] = 0
                    usage[proc_type][key][str_value] += 1

        return usage

    # ========== Templates ==========

    def get_templates(self) -> dict:
        """Get predefined procedure templates."""
        return PROCEDURE_TEMPLATES

    def get_category_templates(self, category: str) -> Optional[dict]:
        """Get templates for a specific category."""
        return PROCEDURE_TEMPLATES.get(category.lower())


def get_procedure_service(db: AsyncSession) -> ProcedureService:
    """Factory function for procedure service."""
    return ProcedureService(db)
