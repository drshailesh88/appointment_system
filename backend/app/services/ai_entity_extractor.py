"""
Entity Extractor for AI Assistant.

Phase 16b: Conversational Actions

Extracts entities from user messages for action execution:
- Dates (today, tomorrow, next Monday, specific dates)
- Times (3pm, 15:30, afternoon)
- Patients (by name or phone)
- Doctors (by name)
"""

import logging
import re
from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.patient import Patient

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extract entities from user messages."""

    def __init__(self, db: Session):
        self.db = db

    async def extract_patient(
        self,
        message: str,
        clinic_id: UUID,
        context_patient_id: Optional[UUID] = None,
    ) -> Optional[Patient]:
        """
        Extract patient from message.

        Args:
            message: User message
            clinic_id: Clinic ID for search scope
            context_patient_id: Patient from conversation context

        Returns:
            Patient or None
        """
        # If patient in context, use it
        if context_patient_id:
            patient = self.db.query(Patient).filter(
                Patient.id == context_patient_id,
                Patient.clinic_id == clinic_id,
            ).first()
            if patient:
                return patient

        # Extract phone number (10 digits)
        phone_match = re.search(r'\b(\d{10})\b', message)
        if phone_match:
            phone = phone_match.group(1)
            patient = self.db.query(Patient).filter(
                Patient.phone.contains(phone),
                Patient.clinic_id == clinic_id,
            ).first()
            if patient:
                return patient

        # Extract name (capitalized words)
        # Look for patterns like "Rajesh Kumar", "Dr. Sharma", etc.
        name_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',  # Full name
            r'\b([A-Z][a-z]+)\b',  # Single name
        ]

        for pattern in name_patterns:
            matches = re.findall(pattern, message)
            for name in matches:
                # Search by name
                patient = self.db.query(Patient).filter(
                    or_(
                        Patient.first_name.ilike(f"%{name}%"),
                        Patient.last_name.ilike(f"%{name}%"),
                    ),
                    Patient.clinic_id == clinic_id,
                ).first()
                if patient:
                    return patient

        return None

    async def extract_doctor(
        self,
        message: str,
        clinic_id: UUID,
        context_doctor_id: Optional[UUID] = None,
    ) -> Optional[Doctor]:
        """
        Extract doctor from message.

        Args:
            message: User message
            clinic_id: Clinic ID
            context_doctor_id: Doctor from context

        Returns:
            Doctor or None
        """
        # If doctor in context, use it
        if context_doctor_id:
            doctor = self.db.query(Doctor).filter(
                Doctor.id == context_doctor_id,
                Doctor.clinic_id == clinic_id,
            ).first()
            if doctor:
                return doctor

        # Extract doctor name (with or without "Dr.")
        doc_patterns = [
            r'(?:Dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]

        for pattern in doc_patterns:
            matches = re.findall(pattern, message)
            for name in matches:
                doctor = self.db.query(Doctor).filter(
                    or_(
                        Doctor.first_name.ilike(f"%{name}%"),
                        Doctor.last_name.ilike(f"%{name}%"),
                    ),
                    Doctor.clinic_id == clinic_id,
                ).first()
                if doctor:
                    return doctor

        # If no doctor specified, return default (first active doctor)
        return self.db.query(Doctor).filter(
            Doctor.clinic_id == clinic_id,
            Doctor.is_active == True,
        ).first()

    def extract_date(self, message: str, reference_date: Optional[date] = None) -> Optional[date]:
        """
        Extract date from message.

        Supports:
        - Relative dates: today, tomorrow, day after tomorrow
        - Day names: Monday, Tuesday, etc. (assumes next occurrence)
        - Specific dates: 15th January, Jan 15, 2026-01-15

        Args:
            message: User message
            reference_date: Reference date (defaults to today)

        Returns:
            date or None
        """
        today = reference_date or date.today()
        message_lower = message.lower()

        # Relative dates
        if re.search(r'\btoday\b|\baaj\b', message_lower):
            return today
        if re.search(r'\btomorrow\b|\bkal\b', message_lower):
            return today + timedelta(days=1)
        if re.search(r'\bday after tomorrow\b|\bparso\b', message_lower):
            return today + timedelta(days=2)
        if re.search(r'\byesterday\b', message_lower):
            return today - timedelta(days=1)

        # Week/month references
        if re.search(r'\bthis week\b', message_lower):
            # Return next weekday (Monday-Friday)
            days_ahead = 1
            if today.weekday() >= 4:  # Friday or later
                days_ahead = 7 - today.weekday()  # Go to Monday
            return today + timedelta(days=days_ahead)

        if re.search(r'\bnext week\b', message_lower):
            days_to_monday = 7 - today.weekday()
            return today + timedelta(days=days_to_monday)

        if re.search(r'\bnext month\b', message_lower):
            if today.month == 12:
                return date(today.year + 1, 1, 1)
            else:
                return date(today.year, today.month + 1, 1)

        # Day names (Monday, Tuesday, etc.)
        days = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
        }

        for day_name, day_num in days.items():
            if re.search(rf'\b{day_name}\b', message_lower):
                days_ahead = (day_num - today.weekday()) % 7
                if days_ahead == 0:  # Today is that day, assume next week
                    days_ahead = 7
                return today + timedelta(days=days_ahead)

        # Specific dates: "15th January", "Jan 15", "15/01/2026"
        # Format: DD/MM/YYYY
        date_match = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', message)
        if date_match:
            day, month, year = date_match.groups()
            year = int(year)
            if year < 100:  # 2-digit year
                year += 2000
            try:
                return date(year, int(month), int(day))
            except ValueError:
                logger.warning(f"Invalid date: {day}/{month}/{year}")

        # Format: YYYY-MM-DD
        date_match = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', message)
        if date_match:
            year, month, day = date_match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                logger.warning(f"Invalid date: {year}-{month}-{day}")

        # Format: "15th January", "Jan 15"
        months = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
        }

        for month_name, month_num in months.items():
            # "15th January" or "January 15th"
            pattern = rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{month_name}\b|\b{month_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b'
            date_match = re.search(pattern, message_lower)
            if date_match:
                day = date_match.group(1) or date_match.group(2)
                try:
                    year = today.year
                    extracted_date = date(year, month_num, int(day))
                    # If date is in past, assume next year
                    if extracted_date < today:
                        extracted_date = date(year + 1, month_num, int(day))
                    return extracted_date
                except ValueError:
                    logger.warning(f"Invalid date: {day} {month_name}")

        return None

    def extract_time(self, message: str) -> Optional[time]:
        """
        Extract time from message.

        Supports:
        - 12-hour: 3pm, 3:30pm, 03:30 PM
        - 24-hour: 15:30, 1530
        - Words: morning, afternoon, evening

        Args:
            message: User message

        Returns:
            time or None
        """
        message_lower = message.lower()

        # 12-hour format: 3pm, 3:30pm
        time_match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', message_lower)
        if time_match:
            hour, minute, meridiem = time_match.groups()
            hour = int(hour)
            minute = int(minute) if minute else 0

            if meridiem == 'pm' and hour != 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0

            try:
                return time(hour, minute)
            except ValueError:
                logger.warning(f"Invalid time: {hour}:{minute} {meridiem}")

        # 24-hour format: 15:30
        time_match = re.search(r'\b(\d{1,2}):(\d{2})\b', message)
        if time_match:
            hour, minute = time_match.groups()
            try:
                return time(int(hour), int(minute))
            except ValueError:
                logger.warning(f"Invalid time: {hour}:{minute}")

        # 4-digit format: 1530
        time_match = re.search(r'\b(\d{2})(\d{2})\b', message)
        if time_match:
            hour, minute = time_match.groups()
            hour_int, minute_int = int(hour), int(minute)
            if 0 <= hour_int <= 23 and 0 <= minute_int <= 59:
                try:
                    return time(hour_int, minute_int)
                except ValueError:
                    pass

        # Word-based times
        if re.search(r'\bmorning\b', message_lower):
            return time(9, 0)  # 9 AM
        if re.search(r'\bafternoon\b|\blunch\b', message_lower):
            return time(14, 0)  # 2 PM
        if re.search(r'\bevening\b', message_lower):
            return time(18, 0)  # 6 PM
        if re.search(r'\bnight\b', message_lower):
            return time(20, 0)  # 8 PM

        return None

    def extract_urgency(self, message: str) -> str:
        """
        Extract urgency level from message.

        Returns:
            'high', 'medium', or 'low'
        """
        message_lower = message.lower()

        if any(word in message_lower for word in ['urgent', 'emergency', 'asap', 'immediately']):
            return 'high'
        elif any(word in message_lower for word in ['soon', 'priority']):
            return 'medium'
        else:
            return 'low'

    def extract_reason(self, message: str) -> Optional[str]:
        """
        Extract appointment reason/complaint from message.

        Args:
            message: User message

        Returns:
            Extracted reason or None
        """
        # Look for patterns like "for X", "because of X", "reason: X"
        patterns = [
            r'(?:for|because of|reason:?)\s+(.+?)(?:\.|$)',
            r'(?:complaint:?|problem:?)\s+(.+?)(?:\.|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None
