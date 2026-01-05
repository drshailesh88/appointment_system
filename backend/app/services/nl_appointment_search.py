"""
Natural Language Appointment Search Service.

AI-powered appointment search using conversational queries with LLM-based
query understanding and hybrid search execution.
"""

import json
import logging
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.nl_search import (
    AggregateData,
    AggregateResponse,
    AppointmentSearchResult,
    NLSearchResponse,
    ParsedDateFilter,
    ParsedQuery,
    SearchHistoryEntry,
    SearchSuggestion,
)
from app.services.rag_search import RAGSearchService, SearchCollection, get_search_service

logger = logging.getLogger(__name__)


class NLAppointmentSearchService:
    """
    Natural Language Appointment Search Service.

    Features:
    - LLM-powered query parsing (using Ollama + Qwen)
    - Entity extraction (dates, names, status, etc.)
    - Hybrid search (semantic + SQL filters)
    - Query suggestions
    - Aggregate queries
    - Graceful fallback when LLM unavailable
    """

    def __init__(
        self,
        ollama_base_url: str | None = None,
        ollama_model: str | None = None,
    ):
        """
        Initialize NL search service.

        Args:
            ollama_base_url: Ollama API base URL
            ollama_model: Model name for query understanding
        """
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.ollama_model = ollama_model or settings.ollama_model
        self.rag_service: RAGSearchService = get_search_service()
        self._search_history: dict[str, list[SearchHistoryEntry]] = {}

    async def search(
        self,
        query: str,
        clinic_id: UUID,
        db: AsyncSession,
        context: dict[str, Any] | None = None,
    ) -> NLSearchResponse:
        """
        Execute natural language appointment search.

        Args:
            query: Natural language query
            clinic_id: Clinic to search within
            db: Database session
            context: Optional context (filters, preferences)

        Returns:
            NLSearchResponse with results and metadata
        """
        import time
        start_time = time.time()

        # Parse query using LLM
        parsed_query = await self._parse_query(query, context)

        # Execute search based on query type
        if parsed_query.query_type == "aggregate":
            # Convert aggregate to search for now
            # (aggregate endpoint handles true aggregates)
            pass

        # Build SQL filters from parsed query
        filters = await self._build_filters(parsed_query, clinic_id, db)

        # Execute database query
        stmt = (
            select(Appointment)
            .options(
                joinedload(Appointment.patient),
                joinedload(Appointment.doctor),
            )
            .filter(*filters)
            .order_by(Appointment.scheduled_start.desc())
            .limit(50)
        )

        result = await db.execute(stmt)
        appointments = result.unique().scalars().all()

        # Convert to search results with relevance scoring
        search_results = []
        for appt in appointments:
            relevance_score = self._calculate_relevance(appt, parsed_query)
            match_reason = self._explain_match(appt, parsed_query)

            search_results.append(
                AppointmentSearchResult(
                    id=appt.id,
                    patient_id=appt.patient_id,
                    patient_name=appt.patient.full_name,
                    doctor_id=appt.doctor_id,
                    doctor_name=appt.doctor.name,
                    scheduled_start=appt.scheduled_start,
                    duration_minutes=appt.duration_minutes,
                    status=appt.status,
                    appointment_type=appt.appointment_type,
                    chief_complaint=appt.chief_complaint,
                    token_number=appt.token_number,
                    relevance_score=relevance_score,
                    match_reason=match_reason,
                )
            )

        # Sort by relevance
        search_results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Generate summary
        summary = self._generate_summary(query, search_results, parsed_query)

        # Generate suggestions
        suggestions = self._generate_suggestions(parsed_query, search_results)

        search_time_ms = (time.time() - start_time) * 1000

        # Store in history
        self._add_to_history(clinic_id, query, len(search_results))

        return NLSearchResponse(
            results=search_results,
            summary=summary,
            suggestions=suggestions,
            parsed_query=parsed_query,
            total_count=len(search_results),
            search_time_ms=search_time_ms,
        )

    async def parse_query(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> ParsedQuery:
        """
        Parse query without executing search.

        Args:
            query: Natural language query
            context: Optional context

        Returns:
            ParsedQuery with structured interpretation
        """
        return await self._parse_query(query, context)

    async def aggregate_query(
        self,
        query: str,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> AggregateResponse:
        """
        Execute aggregate query (count, stats, etc.).

        Args:
            query: Natural language aggregate query
            clinic_id: Clinic to search within
            db: Database session

        Returns:
            AggregateResponse with answer and data
        """
        # Parse query
        parsed_query = await self._parse_query(query, {"query_type": "aggregate"})

        # Build filters
        filters = await self._build_filters(parsed_query, clinic_id, db)

        # Execute count query
        stmt = select(Appointment).filter(*filters)
        result = await db.execute(stmt)
        appointments = result.scalars().all()

        # Calculate aggregates
        total_count = len(appointments)

        # Breakdown by status
        status_breakdown = {}
        for appt in appointments:
            status_breakdown[appt.status] = status_breakdown.get(appt.status, 0) + 1

        # Generate natural language answer
        answer = self._generate_aggregate_answer(query, total_count, status_breakdown, parsed_query)

        # Determine visualization hint
        viz_hint = self._suggest_visualization(parsed_query, status_breakdown)

        return AggregateResponse(
            answer=answer,
            data=AggregateData(
                count=total_count,
                breakdown=status_breakdown,
            ),
            visualization_hint=viz_hint,
            query=query,
        )

    def get_search_history(
        self,
        clinic_id: UUID,
        limit: int = 20,
    ) -> list[SearchHistoryEntry]:
        """
        Get recent search history for a clinic.

        Args:
            clinic_id: Clinic ID
            limit: Max entries to return

        Returns:
            List of recent searches
        """
        history = self._search_history.get(str(clinic_id), [])
        return history[:limit]

    def get_suggestions(self, context: dict[str, Any] | None = None) -> list[SearchSuggestion]:
        """
        Get query suggestions based on context.

        Args:
            context: Optional context (current date, etc.)

        Returns:
            List of suggested queries
        """
        suggestions = [
            SearchSuggestion(
                text="appointments tomorrow",
                category="time",
                icon="📅",
            ),
            SearchSuggestion(
                text="this week's schedule",
                category="time",
                icon="📆",
            ),
            SearchSuggestion(
                text="cancelled appointments",
                category="status",
                icon="❌",
            ),
            SearchSuggestion(
                text="pending confirmations",
                category="status",
                icon="⏳",
            ),
            SearchSuggestion(
                text="no-shows this month",
                category="status",
                icon="👻",
            ),
            SearchSuggestion(
                text="emergency appointments",
                category="type",
                icon="🚨",
            ),
        ]

        return suggestions

    async def _parse_query(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> ParsedQuery:
        """
        Parse natural language query using LLM.

        Args:
            query: User's query
            context: Optional context

        Returns:
            ParsedQuery with extracted entities and filters
        """
        try:
            # Build LLM prompt
            system_prompt = self._build_parsing_prompt()
            user_prompt = f"Query: {query}"

            if context:
                user_prompt += f"\nContext: {json.dumps(context)}"

            # Call Ollama
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": self.ollama_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                result = response.json()

            # Parse LLM response
            llm_output = result.get("message", {}).get("content", "{}")
            parsed = self._parse_llm_output(llm_output, query)
            return parsed

        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return self._fallback_parse(query)

    def _build_parsing_prompt(self) -> str:
        """Build system prompt for query parsing."""
        today = date.today()

        return f"""You are an assistant for parsing appointment search queries in a medical clinic.

Today's date is: {today.isoformat()} ({today.strftime('%A')})

Parse the user's query and extract:
1. **Date filters**: exact dates, relative dates (tomorrow, next week, etc.), date ranges
2. **Patient names**: full or partial names
3. **Doctor names**: full or partial names (may include "Dr." prefix)
4. **Status filters**: scheduled, confirmed, cancelled, no_show, completed, etc.
5. **Appointment types**: new_consultation, follow_up, emergency, teleconsultation
6. **Query type**: "search" (find appointments) or "aggregate" (count/stats)

Respond in JSON format:
{{
    "query_type": "search" or "aggregate",
    "confidence": 0.0 to 1.0,
    "entities": {{
        "patient_name": "name or null",
        "doctor_name": "name or null",
        "status": ["list of statuses"] or null,
        "appointment_type": "type or null",
        "date_description": "relative date description or null"
    }},
    "filters": {{
        "start_date": "YYYY-MM-DD or null",
        "end_date": "YYYY-MM-DD or null",
        "exact_date": "YYYY-MM-DD or null"
    }},
    "needs_clarification": true/false,
    "clarification_question": "question to ask user or null"
}}

Examples:
- "appointments tomorrow" → exact_date: {(today + timedelta(days=1)).isoformat()}
- "this week" → start_date: (start of week), end_date: (end of week)
- "next Monday" → exact_date: (next Monday's date)
- "last week" → start_date: (7 days ago), end_date: (today)
- "Dr. Sharma's appointments" → doctor_name: "Sharma"
- "cancelled appointments" → status: ["cancelled"]
- "no-shows this month" → status: ["no_show"], date range: (month start to today)
- "how many appointments today" → query_type: "aggregate", exact_date: {today.isoformat()}

Handle Hindi/English mixed queries. Be smart about relative dates."""

    def _parse_llm_output(self, llm_output: str, original_query: str) -> ParsedQuery:
        """Parse LLM JSON output into ParsedQuery."""
        try:
            data = json.loads(llm_output)
        except json.JSONDecodeError:
            # Try to extract JSON
            match = re.search(r"\{.*\}", llm_output, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return self._fallback_parse(original_query)
            else:
                return self._fallback_parse(original_query)

        # Extract date filter
        filters = data.get("filters", {})
        parsed_date = ParsedDateFilter(
            start_date=self._parse_date_str(filters.get("start_date")),
            end_date=self._parse_date_str(filters.get("end_date")),
            exact_date=self._parse_date_str(filters.get("exact_date")),
            relative_description=data.get("entities", {}).get("date_description"),
        )

        entities = data.get("entities", {})

        return ParsedQuery(
            entities=entities,
            filters=filters,
            query_type=data.get("query_type", "search"),
            confidence=float(data.get("confidence", 0.5)),
            parsed_date=parsed_date,
            patient_name=entities.get("patient_name"),
            doctor_name=entities.get("doctor_name"),
            status_filter=entities.get("status"),
            appointment_type=entities.get("appointment_type"),
            needs_clarification=data.get("needs_clarification", False),
            clarification_question=data.get("clarification_question"),
        )

    def _fallback_parse(self, query: str) -> ParsedQuery:
        """Fallback parsing using regex when LLM unavailable."""
        query_lower = query.lower()

        # Detect query type
        aggregate_keywords = ["how many", "count", "total", "number of"]
        query_type = "aggregate" if any(kw in query_lower for kw in aggregate_keywords) else "search"

        # Extract status
        status_map = {
            "cancelled": ["cancelled"],
            "cancel": ["cancelled"],
            "confirmed": ["confirmed"],
            "pending": ["scheduled"],
            "no-show": ["no_show"],
            "no show": ["no_show"],
            "completed": ["completed"],
        }

        status_filter = None
        for keyword, statuses in status_map.items():
            if keyword in query_lower:
                status_filter = statuses
                break

        # Extract date
        parsed_date = self._parse_date_from_query(query_lower)

        # Extract names (simple heuristic)
        patient_name = None
        doctor_name = None

        if "dr." in query_lower or "doctor" in query_lower:
            # Try to extract doctor name after "dr." or "doctor"
            match = re.search(r"dr\.?\s+(\w+)", query_lower)
            if match:
                doctor_name = match.group(1).capitalize()

        return ParsedQuery(
            entities={
                "patient_name": patient_name,
                "doctor_name": doctor_name,
                "status": status_filter,
            },
            filters={},
            query_type=query_type,
            confidence=0.5,
            parsed_date=parsed_date,
            patient_name=patient_name,
            doctor_name=doctor_name,
            status_filter=status_filter,
        )

    def _parse_date_from_query(self, query_lower: str) -> ParsedDateFilter:
        """Parse date from query using keywords."""
        today = date.today()

        # Exact date matches
        if "today" in query_lower or "aaj" in query_lower:
            return ParsedDateFilter(exact_date=today, relative_description="today")
        elif "tomorrow" in query_lower or "kal" in query_lower:
            return ParsedDateFilter(
                exact_date=today + timedelta(days=1),
                relative_description="tomorrow",
            )
        elif "yesterday" in query_lower:
            return ParsedDateFilter(
                exact_date=today - timedelta(days=1),
                relative_description="yesterday",
            )

        # Week ranges
        elif "this week" in query_lower:
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return ParsedDateFilter(start_date=start, end_date=end, relative_description="this week")
        elif "next week" in query_lower:
            start = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
            end = start + timedelta(days=6)
            return ParsedDateFilter(start_date=start, end_date=end, relative_description="next week")
        elif "last week" in query_lower:
            start = today - timedelta(days=today.weekday()) - timedelta(weeks=1)
            end = start + timedelta(days=6)
            return ParsedDateFilter(start_date=start, end_date=end, relative_description="last week")

        # Month ranges
        elif "this month" in query_lower:
            start = today.replace(day=1)
            return ParsedDateFilter(start_date=start, end_date=today, relative_description="this month")

        return ParsedDateFilter()

    def _parse_date_str(self, date_str: str | None) -> date | None:
        """Parse ISO date string."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    async def _build_filters(
        self,
        parsed_query: ParsedQuery,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> list:
        """Build SQLAlchemy filters from parsed query."""
        filters = [Appointment.clinic_id == clinic_id]

        # Date filters
        if parsed_query.parsed_date:
            if parsed_query.parsed_date.exact_date:
                target_date = parsed_query.parsed_date.exact_date
                filters.append(
                    and_(
                        Appointment.scheduled_start >= datetime.combine(target_date, time.min),
                        Appointment.scheduled_start < datetime.combine(
                            target_date + timedelta(days=1), time.min
                        ),
                    )
                )
            elif parsed_query.parsed_date.start_date and parsed_query.parsed_date.end_date:
                filters.append(
                    and_(
                        Appointment.scheduled_start >= datetime.combine(
                            parsed_query.parsed_date.start_date, time.min
                        ),
                        Appointment.scheduled_start <= datetime.combine(
                            parsed_query.parsed_date.end_date, time.max
                        ),
                    )
                )

        # Status filters
        if parsed_query.status_filter:
            filters.append(Appointment.status.in_(parsed_query.status_filter))

        # Appointment type
        if parsed_query.appointment_type:
            filters.append(Appointment.appointment_type == parsed_query.appointment_type)

        # Patient name filter
        if parsed_query.patient_name:
            # Join with patient and filter by name
            filters.append(
                or_(
                    Patient.first_name.ilike(f"%{parsed_query.patient_name}%"),
                    Patient.last_name.ilike(f"%{parsed_query.patient_name}%"),
                )
            )

        # Doctor name filter
        if parsed_query.doctor_name:
            filters.append(Doctor.name.ilike(f"%{parsed_query.doctor_name}%"))

        return filters

    def _calculate_relevance(self, appointment: Appointment, parsed_query: ParsedQuery) -> float:
        """Calculate relevance score for an appointment."""
        score = 0.5  # Base score

        # Boost for exact date match
        if parsed_query.parsed_date and parsed_query.parsed_date.exact_date:
            if appointment.scheduled_start.date() == parsed_query.parsed_date.exact_date:
                score += 0.3

        # Boost for status match
        if parsed_query.status_filter and appointment.status in parsed_query.status_filter:
            score += 0.2

        # Recent appointments score higher
        days_diff = abs((appointment.scheduled_start.date() - date.today()).days)
        recency_boost = max(0, 1.0 - (days_diff / 30)) * 0.1
        score += recency_boost

        return min(1.0, score)

    def _explain_match(self, appointment: Appointment, parsed_query: ParsedQuery) -> str:
        """Explain why this appointment matched the query."""
        reasons = []

        if parsed_query.parsed_date and parsed_query.parsed_date.relative_description:
            reasons.append(f"Matches '{parsed_query.parsed_date.relative_description}'")

        if parsed_query.status_filter and appointment.status in parsed_query.status_filter:
            reasons.append(f"Status: {appointment.status}")

        if parsed_query.patient_name:
            reasons.append(f"Patient name match")

        if parsed_query.doctor_name:
            reasons.append(f"Doctor name match")

        return " | ".join(reasons) if reasons else "Matched filters"

    def _generate_summary(
        self,
        query: str,
        results: list[AppointmentSearchResult],
        parsed_query: ParsedQuery,
    ) -> str:
        """Generate natural language summary of results."""
        count = len(results)

        if count == 0:
            return f"No appointments found for '{query}'."

        # Build summary based on filters
        parts = [f"Found {count} appointment{'s' if count != 1 else ''}"]

        if parsed_query.parsed_date and parsed_query.parsed_date.relative_description:
            parts.append(f"for {parsed_query.parsed_date.relative_description}")

        if parsed_query.doctor_name:
            parts.append(f"with Dr. {parsed_query.doctor_name}")

        if parsed_query.patient_name:
            parts.append(f"for patient {parsed_query.patient_name}")

        if parsed_query.status_filter:
            status_str = ", ".join(parsed_query.status_filter)
            parts.append(f"with status: {status_str}")

        return " ".join(parts) + "."

    def _generate_suggestions(
        self,
        parsed_query: ParsedQuery,
        results: list[AppointmentSearchResult],
    ) -> list[SearchSuggestion]:
        """Generate follow-up query suggestions."""
        suggestions = []

        # Suggest filtering by status if not already filtered
        if not parsed_query.status_filter and results:
            suggestions.append(
                SearchSuggestion(
                    text="Show only confirmed appointments",
                    category="status",
                    icon="✅",
                )
            )

        # Suggest time-based refinements
        if not parsed_query.parsed_date:
            suggestions.append(
                SearchSuggestion(
                    text="appointments tomorrow",
                    category="time",
                    icon="📅",
                )
            )

        # Suggest broadening if few results
        if len(results) < 3:
            suggestions.append(
                SearchSuggestion(
                    text="all appointments this week",
                    category="time",
                    icon="📆",
                )
            )

        return suggestions[:3]  # Limit to 3 suggestions

    def _generate_aggregate_answer(
        self,
        query: str,
        count: int,
        breakdown: dict[str, int],
        parsed_query: ParsedQuery,
    ) -> str:
        """Generate natural language answer for aggregate query."""
        answer_parts = []

        # Main count
        if parsed_query.parsed_date and parsed_query.parsed_date.relative_description:
            answer_parts.append(
                f"There are {count} appointments {parsed_query.parsed_date.relative_description}"
            )
        else:
            answer_parts.append(f"There are {count} appointments")

        # Add breakdown if available
        if breakdown and len(breakdown) > 1:
            breakdown_str = ", ".join([f"{v} {k}" for k, v in breakdown.items()])
            answer_parts.append(f"({breakdown_str})")

        return ". ".join(answer_parts) + "."

    def _suggest_visualization(
        self,
        parsed_query: ParsedQuery,
        breakdown: dict[str, int],
    ) -> str | None:
        """Suggest visualization type for aggregate data."""
        if breakdown and len(breakdown) > 1:
            if len(breakdown) <= 5:
                return "pie"  # Good for status breakdown
            else:
                return "bar"  # Better for many categories

        return None

    def _add_to_history(self, clinic_id: UUID, query: str, result_count: int):
        """Add search to history."""
        clinic_key = str(clinic_id)

        if clinic_key not in self._search_history:
            self._search_history[clinic_key] = []

        # Categorize query
        query_lower = query.lower()
        if any(word in query_lower for word in ["tomorrow", "today", "week", "month"]):
            category = "time"
        elif any(word in query_lower for word in ["cancelled", "confirmed", "pending"]):
            category = "status"
        elif "dr." in query_lower or "doctor" in query_lower:
            category = "doctor"
        else:
            category = "general"

        entry = SearchHistoryEntry(
            id=f"search_{datetime.now().timestamp()}",
            query=query,
            timestamp=datetime.now(),
            result_count=result_count,
            category=category,
        )

        self._search_history[clinic_key].insert(0, entry)

        # Keep last 100 searches
        self._search_history[clinic_key] = self._search_history[clinic_key][:100]


# Singleton instance
_nl_search_service: Optional[NLAppointmentSearchService] = None


def get_nl_search_service() -> NLAppointmentSearchService:
    """Get or create the NL search service singleton."""
    global _nl_search_service
    if _nl_search_service is None:
        _nl_search_service = NLAppointmentSearchService()
    return _nl_search_service
