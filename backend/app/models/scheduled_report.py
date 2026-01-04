"""
Scheduled Report model for automated report generation.

Allows clinics to schedule recurring reports to be generated and emailed:
- Daily appointment summaries
- Weekly/monthly revenue reports
- Doctor performance reports
- Custom analytics reports
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReportType(str, Enum):
    """Types of reports that can be generated."""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    MONTHLY_SUMMARY = "monthly_summary"
    DOCTOR_PERFORMANCE = "doctor_performance"
    REVENUE_REPORT = "revenue_report"
    PATIENT_DEMOGRAPHICS = "patient_demographics"
    NO_SHOW_ANALYSIS = "no_show_analysis"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report output formats."""
    PDF = "pdf"
    EXCEL = "xlsx"
    CSV = "csv"


class ReportFrequency(str, Enum):
    """Report generation frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Use cron expression


class ScheduledReport(Base, TimestampMixin):
    """
    Scheduled report configuration.

    Defines automated reports that are generated and sent via email.
    """

    __tablename__ = "scheduled_reports"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Clinic
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )

    # Report configuration
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    report_format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ReportFormat.PDF.value,
    )

    # Schedule
    frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReportFrequency.WEEKLY.value,
    )
    cron_expression: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )  # For custom schedules (e.g., "0 9 * * 1" = Mondays at 9 AM)

    # Recipients
    recipients: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # List of email addresses: ["admin@clinic.com", "doctor@clinic.com"]

    # Report parameters (JSON for flexibility)
    parameters: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )  # e.g., {"doctor_id": "...", "include_charts": true}

    # Execution tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_run_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )  # "success", "failed", "pending"
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    # Metadata
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Created by
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Relationships
    clinic = relationship("Clinic", backref="scheduled_reports")
    created_by = relationship("User", backref="scheduled_reports")

    def __repr__(self) -> str:
        return f"<ScheduledReport {self.name} ({self.frequency})>"

    @property
    def is_due(self) -> bool:
        """Check if report is due for generation."""
        if not self.is_active:
            return False
        if not self.next_run_at:
            return True  # Never run, needs to run
        return datetime.now(timezone.utc) >= self.next_run_at

    def mark_success(self):
        """Mark last run as successful."""
        self.last_run_at = datetime.now(timezone.utc)
        self.last_run_status = "success"
        self.last_error = None

    def mark_failed(self, error: str):
        """Mark last run as failed."""
        self.last_run_at = datetime.now(timezone.utc)
        self.last_run_status = "failed"
        self.last_error = error
