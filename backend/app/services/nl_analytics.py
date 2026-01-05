"""
Natural Language Analytics Service.

Phase 16A: Integrates AI query parsing with real analytics functions.

This service acts as the bridge between the AI assistant's function calls
and the actual analytics service, converting parsed queries into real data.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.procedure import Procedure
from app.services.analytics import AnalyticsService
from app.services.ai_assistant import FunctionCall, FunctionName

logger = logging.getLogger(__name__)


@dataclass
class NLQueryResult:
    """Result of a natural language query."""

    natural_response: str  # Human-readable response
    structured_data: dict[str, Any]  # Data for UI rendering
    visualization_type: Optional[str] = None  # bar_chart, line_chart, table, metric
    sql_generated: Optional[str] = None  # SQL query (for debugging)
    suggestions: list[str] = None  # Follow-up suggestions

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class NaturalLanguageAnalytics:
    """
    Natural Language Analytics Service.

    Executes analytics queries based on parsed function calls from the AI.
    Converts results into natural language responses with structured data.
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.analytics = AnalyticsService(db)

    async def execute_query(
        self,
        function_call: FunctionCall,
        clinic_id: UUID,
    ) -> NLQueryResult:
        """
        Execute an analytics query based on parsed function call.

        Args:
            function_call: Parsed function call from AI
            clinic_id: Clinic to query

        Returns:
            NLQueryResult with response and data
        """
        func = function_call.function
        args = function_call.arguments

        try:
            if func == FunctionName.GET_PROCEDURE_STATS:
                return await self._get_procedure_stats(clinic_id, args)
            elif func == FunctionName.GET_REVENUE_ANALYTICS:
                return await self._get_revenue_analytics(clinic_id, args)
            elif func == FunctionName.GET_APPOINTMENT_STATS:
                return await self._get_appointment_stats(clinic_id, args)
            elif func == FunctionName.SEARCH_PATIENTS:
                return await self._search_patients(clinic_id, args)
            elif func == FunctionName.GET_DOCTOR_STATS:
                return await self._get_doctor_stats(clinic_id, args)
            else:
                return NLQueryResult(
                    natural_response="I'm not sure how to handle that query.",
                    structured_data={},
                    suggestions=["Try asking about procedures, revenue, or appointments"],
                )

        except Exception as e:
            logger.error(f"Query execution error: {e}", exc_info=True)
            return NLQueryResult(
                natural_response=f"I encountered an error processing your query: {str(e)}",
                structured_data={"error": str(e)},
                suggestions=["Try rephrasing your question", "Check date ranges"],
            )

    async def _get_procedure_stats(
        self,
        clinic_id: UUID,
        args: dict,
    ) -> NLQueryResult:
        """Get procedure statistics."""
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        doctor_id = args.get("doctor_id")
        procedure_type = args.get("procedure_type")
        category = args.get("category")

        # Build query
        filters = [
            Procedure.clinic_id == clinic_id,
            Procedure.performed_at >= datetime.combine(start_date, datetime.min.time()),
            Procedure.performed_at <= datetime.combine(end_date, datetime.max.time()),
        ]

        if doctor_id:
            filters.append(Procedure.doctor_id == doctor_id)
        if procedure_type:
            filters.append(Procedure.procedure_type.ilike(f"%{procedure_type}%"))
        if category:
            filters.append(Procedure.category.ilike(f"%{category}%"))

        # Total count
        count_result = await self.db.execute(
            select(func.count()).where(and_(*filters))
        )
        total = count_result.scalar() or 0

        # By category
        category_result = await self.db.execute(
            select(
                Procedure.category,
                func.count().label("count"),
                func.sum(Procedure.billed_amount).label("billed"),
            )
            .where(and_(*filters))
            .group_by(Procedure.category)
        )
        by_category = {
            row.category or "Unknown": {
                "count": row.count,
                "billed": float(row.billed or 0),
            }
            for row in category_result.all()
        }

        # By procedure type
        type_result = await self.db.execute(
            select(
                Procedure.procedure_type,
                func.count().label("count"),
                func.sum(Procedure.billed_amount).label("billed"),
            )
            .where(and_(*filters))
            .group_by(Procedure.procedure_type)
            .order_by(func.count().desc())
            .limit(10)
        )
        by_type = {
            row.procedure_type or "Unknown": {
                "count": row.count,
                "billed": float(row.billed or 0),
            }
            for row in type_result.all()
        }

        # Total billed
        billed_result = await self.db.execute(
            select(func.coalesce(func.sum(Procedure.billed_amount), 0))
            .where(and_(*filters))
        )
        total_billed = float(billed_result.scalar() or 0)

        # Build structured data
        structured_data = {
            "total": total,
            "by_category": by_category,
            "by_type": by_type,
            "total_billed": total_billed,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        # Build natural language response
        date_range = self._format_date_range(start_date, end_date)
        response_parts = [f"**Procedure Statistics** {date_range}\n"]

        if total == 0:
            response_parts.append("No procedures found in this period.")
        else:
            response_parts.append(f"• **Total Procedures:** {total}")
            response_parts.append(f"• **Total Billed:** ₹{total_billed:,.0f}\n")

            if by_category:
                response_parts.append("**By Category:**")
                for cat, data in sorted(by_category.items(), key=lambda x: x[1]["count"], reverse=True):
                    pct = (data["count"] / total * 100) if total > 0 else 0
                    response_parts.append(f"  - {cat}: {data['count']} ({pct:.0f}%)")
                response_parts.append("")

            if by_type:
                response_parts.append("**Top Procedures:**")
                for ptype, data in list(by_type.items())[:5]:
                    response_parts.append(f"  - {ptype}: {data['count']} (₹{data['billed']:,.0f})")

        natural_response = "\n".join(response_parts)

        # Suggestions
        suggestions = [
            "Breakdown by doctor",
            "Compare to last month",
            "Show procedure trends",
        ]

        return NLQueryResult(
            natural_response=natural_response,
            structured_data=structured_data,
            visualization_type="bar_chart",
            suggestions=suggestions,
        )

    async def _get_revenue_analytics(
        self,
        clinic_id: UUID,
        args: dict,
    ) -> NLQueryResult:
        """Get revenue analytics."""
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        doctor_id = args.get("doctor_id")

        # Get revenue stats from analytics service
        revenue_stats = await self.analytics.get_revenue_stats(
            clinic_id=clinic_id,
            start_date=start_date,
            end_date=end_date,
            doctor_id=doctor_id,
        )

        # Build structured data
        structured_data = {
            "total_revenue": float(revenue_stats.total_revenue),
            "collected": float(revenue_stats.collected),
            "pending": float(revenue_stats.pending),
            "refunded": float(revenue_stats.refunded),
            "collection_rate": revenue_stats.collection_rate,
            "average_invoice": float(revenue_stats.average_invoice),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        # Build natural language response
        date_range = self._format_date_range(start_date, end_date)
        response_parts = [f"**Revenue Summary** {date_range}\n"]

        response_parts.append(f"• **Total Revenue:** ₹{revenue_stats.total_revenue:,.0f}")
        response_parts.append(f"• **Collected:** ₹{revenue_stats.collected:,.0f} ({revenue_stats.collection_rate:.1f}%)")
        response_parts.append(f"• **Pending:** ₹{revenue_stats.pending:,.0f}")

        if revenue_stats.average_invoice > 0:
            response_parts.append(f"• **Average Invoice:** ₹{revenue_stats.average_invoice:,.0f}")

        # Add insights
        response_parts.append("")
        if revenue_stats.collection_rate >= 90:
            response_parts.append("✓ Excellent collection rate!")
        elif revenue_stats.collection_rate >= 75:
            response_parts.append("✓ Good collection rate.")
        else:
            response_parts.append("⚠ Collection rate needs attention.")

        natural_response = "\n".join(response_parts)

        # Suggestions
        suggestions = [
            "Daily revenue breakdown",
            "Outstanding payments",
            "Compare to last month",
        ]

        return NLQueryResult(
            natural_response=natural_response,
            structured_data=structured_data,
            visualization_type="metric",
            suggestions=suggestions,
        )

    async def _get_appointment_stats(
        self,
        clinic_id: UUID,
        args: dict,
    ) -> NLQueryResult:
        """Get appointment statistics."""
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        doctor_id = args.get("doctor_id")

        # Get appointment stats from analytics service
        appt_stats = await self.analytics.get_appointment_stats(
            clinic_id=clinic_id,
            start_date=start_date,
            end_date=end_date,
            doctor_id=doctor_id,
        )

        # Build structured data
        structured_data = {
            "total": appt_stats.total,
            "completed": appt_stats.completed,
            "cancelled": appt_stats.cancelled,
            "no_show": appt_stats.no_show,
            "scheduled": appt_stats.scheduled,
            "completion_rate": appt_stats.completion_rate,
            "cancellation_rate": appt_stats.cancellation_rate,
            "no_show_rate": appt_stats.no_show_rate,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        # Build natural language response
        date_range = self._format_date_range(start_date, end_date)
        response_parts = [f"**Appointment Statistics** {date_range}\n"]

        if appt_stats.total == 0:
            response_parts.append("No appointments found in this period.")
        else:
            response_parts.append(f"• **Total:** {appt_stats.total}")
            response_parts.append(f"• **Completed:** {appt_stats.completed} ({appt_stats.completion_rate:.1f}%)")
            response_parts.append(f"• **Cancelled:** {appt_stats.cancelled} ({appt_stats.cancellation_rate:.1f}%)")
            response_parts.append(f"• **No-show:** {appt_stats.no_show} ({appt_stats.no_show_rate:.1f}%)")
            response_parts.append(f"• **Scheduled:** {appt_stats.scheduled}")

            # Add insights
            response_parts.append("")
            if appt_stats.no_show_rate < 5:
                response_parts.append("✓ Excellent no-show rate!")
            elif appt_stats.no_show_rate < 10:
                response_parts.append("✓ Acceptable no-show rate.")
            else:
                response_parts.append("⚠ High no-show rate - consider sending reminders.")

        natural_response = "\n".join(response_parts)

        # Suggestions
        suggestions = [
            "No-show patterns",
            "Cancellation reasons",
            "Busiest days",
        ]

        return NLQueryResult(
            natural_response=natural_response,
            structured_data=structured_data,
            visualization_type="donut_chart",
            suggestions=suggestions,
        )

    async def _search_patients(
        self,
        clinic_id: UUID,
        args: dict,
    ) -> NLQueryResult:
        """Search for patients."""
        query = args.get("query", "").strip()

        if not query:
            return NLQueryResult(
                natural_response="Please specify what to search for (name, phone, or condition).",
                structured_data={},
                suggestions=["Search for diabetic patients", "Find patient by phone"],
            )

        # Search by name or phone
        filters = [Patient.clinic_id == clinic_id]

        # Check if query is a phone number
        if query.isdigit():
            filters.append(Patient.phone.like(f"%{query}%"))
        else:
            # Search by name or medical condition
            filters.append(
                Patient.full_name.ilike(f"%{query}%")
            )

        # Execute search
        result = await self.db.execute(
            select(Patient)
            .where(and_(*filters))
            .order_by(Patient.created_at.desc())
            .limit(20)
        )
        patients = result.scalars().all()

        # Build structured data
        patient_list = []
        for p in patients:
            patient_list.append({
                "id": str(p.id),
                "name": p.full_name,
                "phone": p.phone,
                "email": p.email,
                "city": p.city,
                "last_visit": None,  # Would need to query appointments
            })

        structured_data = {
            "count": len(patients),
            "patients": patient_list,
            "query": query,
        }

        # Build natural language response
        response_parts = []

        if len(patients) == 0:
            response_parts.append(f"No patients found matching '{query}'.")
            response_parts.append("\nTry searching by:")
            response_parts.append("• Full or partial name")
            response_parts.append("• Phone number")
        else:
            response_parts.append(f"**Found {len(patients)} patient(s)** matching '{query}':\n")

            for i, p in enumerate(patients[:5], 1):
                response_parts.append(f"{i}. **{p.full_name}**")
                response_parts.append(f"   Phone: {p.phone}")
                if p.email:
                    response_parts.append(f"   Email: {p.email}")
                response_parts.append("")

            if len(patients) > 5:
                response_parts.append(f"... and {len(patients) - 5} more.")

        natural_response = "\n".join(response_parts)

        # Suggestions
        suggestions = [
            "Show patient details",
            "Upcoming appointments",
            "Patient history",
        ]

        return NLQueryResult(
            natural_response=natural_response,
            structured_data=structured_data,
            visualization_type="table",
            suggestions=suggestions if patients else ["Try a different search term"],
        )

    async def _get_doctor_stats(
        self,
        clinic_id: UUID,
        args: dict,
    ) -> NLQueryResult:
        """Get doctor performance statistics."""
        start_date = args.get("start_date")
        end_date = args.get("end_date")

        # Get doctor utilization from analytics service
        doctor_utils = await self.analytics.get_doctor_utilization(
            clinic_id=clinic_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Build structured data
        doctor_list = []
        for util in doctor_utils:
            doctor_list.append({
                "doctor_id": str(util.doctor_id),
                "doctor_name": util.doctor_name,
                "total_slots": util.total_slots,
                "booked_slots": util.booked_slots,
                "completed_appointments": util.completed_appointments,
                "utilization_rate": util.utilization_rate,
                "average_duration_minutes": util.average_duration_minutes,
                "revenue_generated": float(util.revenue_generated),
            })

        structured_data = {
            "doctors": doctor_list,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        # Build natural language response
        date_range = self._format_date_range(start_date, end_date)
        response_parts = [f"**Doctor Performance** {date_range}\n"]

        if not doctor_utils:
            response_parts.append("No doctor statistics available for this period.")
        else:
            # Sort by completed appointments
            sorted_doctors = sorted(
                doctor_utils,
                key=lambda x: x.completed_appointments,
                reverse=True,
            )

            for i, util in enumerate(sorted_doctors, 1):
                response_parts.append(f"**{i}. {util.doctor_name}**")
                response_parts.append(f"   • Appointments: {util.completed_appointments}/{util.booked_slots}")
                response_parts.append(f"   • Utilization: {util.utilization_rate:.1f}%")
                response_parts.append(f"   • Avg Duration: {util.average_duration_minutes:.0f} mins")
                response_parts.append("")

            # Add insight
            if sorted_doctors:
                top_doc = sorted_doctors[0]
                response_parts.append(f"🏆 {top_doc.doctor_name} is the top performer!")

        natural_response = "\n".join(response_parts)

        # Suggestions
        suggestions = [
            "Individual doctor breakdown",
            "Revenue by doctor",
            "Utilization trends",
        ]

        return NLQueryResult(
            natural_response=natural_response,
            structured_data=structured_data,
            visualization_type="bar_chart",
            suggestions=suggestions,
        )

    def _format_date_range(self, start_date: date, end_date: date) -> str:
        """Format date range for display."""
        today = date.today()

        if start_date == end_date == today:
            return "(Today)"
        elif start_date == end_date:
            return f"({start_date.strftime('%d %b %Y')})"
        elif start_date.month == end_date.month and start_date.year == end_date.year:
            return f"({start_date.strftime('%d')}-{end_date.strftime('%d %b %Y')})"
        else:
            return f"({start_date.strftime('%d %b')}-{end_date.strftime('%d %b %Y')})"

    async def get_query_suggestions(self, clinic_id: UUID) -> list[str]:
        """
        Get suggested queries based on clinic activity.

        Returns context-aware suggestions like:
        - "How many procedures this week?" (if procedures exist)
        - "Revenue today" (always available)
        - "No-show rate this month" (if appointments exist)
        """
        today = date.today()

        # Check if clinic has recent activity
        has_procedures = await self._has_recent_procedures(clinic_id)
        has_appointments = await self._has_recent_appointments(clinic_id)

        suggestions = [
            "Revenue today",
            "Revenue this month",
            "Appointments today",
            "Appointment stats this week",
        ]

        if has_procedures:
            suggestions.extend([
                "How many procedures this month?",
                "Top procedures by revenue",
            ])

        if has_appointments:
            suggestions.extend([
                "No-show rate this month",
                "Busiest day this week",
            ])

        suggestions.extend([
            "Doctor performance this month",
            "Find patient",
        ])

        return suggestions

    async def _has_recent_procedures(self, clinic_id: UUID) -> bool:
        """Check if clinic has procedures in last 30 days."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Procedure)
            .where(
                and_(
                    Procedure.clinic_id == clinic_id,
                    Procedure.performed_at >= datetime.now() - __import__("datetime").timedelta(days=30),
                )
            )
        )
        return (result.scalar() or 0) > 0

    async def _has_recent_appointments(self, clinic_id: UUID) -> bool:
        """Check if clinic has appointments in last 30 days."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Appointment)
            .where(
                and_(
                    Appointment.clinic_id == clinic_id,
                    Appointment.scheduled_start >= datetime.now() - __import__("datetime").timedelta(days=30),
                )
            )
        )
        return (result.scalar() or 0) > 0


def get_nl_analytics(db: AsyncSession) -> NaturalLanguageAnalytics:
    """Factory function for NL analytics service."""
    return NaturalLanguageAnalytics(db)
