"""
Report Scheduler Service.

Manages scheduled report generation and delivery:
- Processes scheduled reports based on frequency
- Generates reports in background
- Sends reports via email
- Tracks execution history
"""

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.scheduled_report import (
    ScheduledReport,
    ReportFrequency,
    ReportFormat,
)
from app.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class ReportScheduler:
    """
    Report scheduling service.

    Manages automated report generation and delivery.
    """

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: str = "reports@docassist.com",
    ):
        """Initialize report scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Report scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Report scheduler stopped")

    async def schedule_report(self, scheduled_report: ScheduledReport):
        """
        Add a scheduled report to the scheduler.

        Args:
            scheduled_report: ScheduledReport model instance
        """
        job_id = f"report_{scheduled_report.id}"

        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # Create trigger based on frequency
        trigger = self._create_trigger(
            scheduled_report.frequency,
            scheduled_report.cron_expression,
        )

        if trigger:
            self.scheduler.add_job(
                self._generate_and_send_report,
                trigger=trigger,
                id=job_id,
                args=[scheduled_report.id],
                name=f"Report: {scheduled_report.name}",
                replace_existing=True,
            )

            # Calculate next run time
            next_run = self.scheduler.get_job(job_id).next_run_time
            if next_run:
                scheduled_report.next_run_at = next_run

            logger.info(f"Scheduled report '{scheduled_report.name}' with job ID {job_id}")

    async def unschedule_report(self, report_id: UUID):
        """
        Remove a scheduled report from the scheduler.

        Args:
            report_id: ID of the scheduled report
        """
        job_id = f"report_{report_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled report with ID {report_id}")

    async def load_all_scheduled_reports(self):
        """Load all active scheduled reports from database."""
        async for db in get_db():
            try:
                result = await db.execute(
                    select(ScheduledReport).where(
                        ScheduledReport.is_active == True
                    )
                )
                reports = result.scalars().all()

                for report in reports:
                    await self.schedule_report(report)

                logger.info(f"Loaded {len(reports)} scheduled reports")
            except Exception as e:
                logger.error(f"Failed to load scheduled reports: {e}")
            finally:
                break  # Only need one iteration

    def _create_trigger(
        self,
        frequency: str,
        cron_expression: Optional[str] = None,
    ):
        """
        Create APScheduler trigger from frequency or cron expression.

        Args:
            frequency: Report frequency (daily, weekly, monthly)
            cron_expression: Custom cron expression for custom frequency

        Returns:
            APScheduler trigger instance
        """
        if frequency == ReportFrequency.DAILY.value:
            # Daily at 8 AM
            return CronTrigger(hour=8, minute=0)
        elif frequency == ReportFrequency.WEEKLY.value:
            # Weekly on Monday at 9 AM
            return CronTrigger(day_of_week='mon', hour=9, minute=0)
        elif frequency == ReportFrequency.MONTHLY.value:
            # Monthly on 1st at 10 AM
            return CronTrigger(day=1, hour=10, minute=0)
        elif frequency == ReportFrequency.CUSTOM.value and cron_expression:
            # Parse custom cron expression
            try:
                return CronTrigger.from_crontab(cron_expression)
            except Exception as e:
                logger.error(f"Invalid cron expression '{cron_expression}': {e}")
                return None
        else:
            logger.warning(f"Unknown frequency: {frequency}")
            return None

    async def _generate_and_send_report(self, report_id: UUID):
        """
        Generate and send a scheduled report.

        Args:
            report_id: ID of the scheduled report
        """
        async for db in get_db():
            try:
                # Get scheduled report
                result = await db.execute(
                    select(ScheduledReport).where(ScheduledReport.id == report_id)
                )
                scheduled_report = result.scalar_one_or_none()

                if not scheduled_report:
                    logger.error(f"Scheduled report {report_id} not found")
                    return

                if not scheduled_report.is_active:
                    logger.info(f"Skipping inactive report {report_id}")
                    return

                logger.info(f"Generating report: {scheduled_report.name}")

                # Determine date range based on frequency
                end_date = datetime.now().date()
                if scheduled_report.frequency == ReportFrequency.DAILY.value:
                    start_date = end_date - timedelta(days=1)
                elif scheduled_report.frequency == ReportFrequency.WEEKLY.value:
                    start_date = end_date - timedelta(days=7)
                elif scheduled_report.frequency == ReportFrequency.MONTHLY.value:
                    # Last month
                    first_of_month = end_date.replace(day=1)
                    start_date = (first_of_month - timedelta(days=1)).replace(day=1)
                    end_date = first_of_month - timedelta(days=1)
                else:
                    # Default to last 7 days
                    start_date = end_date - timedelta(days=7)

                # Generate report
                generator = ReportGenerator(db)
                report_bytes = await generator.generate_report(
                    clinic_id=scheduled_report.clinic_id,
                    report_type=scheduled_report.report_type,
                    start_date=start_date,
                    end_date=end_date,
                    format=scheduled_report.report_format,
                    parameters=scheduled_report.parameters or {},
                )

                # Determine file extension
                if scheduled_report.report_format == ReportFormat.PDF.value:
                    file_ext = "pdf"
                    mime_type = "application/pdf"
                elif scheduled_report.report_format == ReportFormat.EXCEL.value:
                    file_ext = "xlsx"
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    file_ext = "csv"
                    mime_type = "text/csv"

                filename = f"{scheduled_report.name.replace(' ', '_')}_{end_date.strftime('%Y%m%d')}.{file_ext}"

                # Send email
                recipients = scheduled_report.recipients
                if isinstance(recipients, dict):
                    recipients = recipients.get('emails', [])

                await self._send_email(
                    recipients=recipients,
                    subject=f"{scheduled_report.name} - {end_date.strftime('%d %B %Y')}",
                    body=f"Please find attached the {scheduled_report.name} for the period {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}.",
                    attachment=report_bytes,
                    filename=filename,
                    mime_type=mime_type,
                )

                # Update execution tracking
                scheduled_report.mark_success()
                next_run = self.scheduler.get_job(f"report_{report_id}").next_run_time
                if next_run:
                    scheduled_report.next_run_at = next_run

                await db.commit()

                logger.info(f"Successfully generated and sent report: {scheduled_report.name}")

            except Exception as e:
                logger.error(f"Failed to generate/send report {report_id}: {e}", exc_info=True)

                # Mark as failed
                try:
                    if scheduled_report:
                        scheduled_report.mark_failed(str(e))
                        await db.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update report status: {commit_error}")
            finally:
                break  # Only need one iteration

    async def _send_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        attachment: bytes,
        filename: str,
        mime_type: str,
    ):
        """
        Send email with report attachment.

        Args:
            recipients: List of email addresses
            subject: Email subject
            body: Email body text
            attachment: Report file bytes
            filename: Attachment filename
            mime_type: Attachment MIME type
        """
        if not recipients:
            logger.warning("No recipients specified for report email")
            return

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Add attachment
            attachment_part = MIMEApplication(attachment, _subtype=mime_type.split('/')[-1])
            attachment_part.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(attachment_part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Sent report email to {len(recipients)} recipients")

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            raise

    async def generate_report_now(
        self,
        report_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> bytes:
        """
        Generate a scheduled report immediately (on-demand).

        Args:
            report_id: ID of the scheduled report
            start_date: Optional custom start date
            end_date: Optional custom end date

        Returns:
            Report file bytes
        """
        async for db in get_db():
            try:
                # Get scheduled report
                result = await db.execute(
                    select(ScheduledReport).where(ScheduledReport.id == report_id)
                )
                scheduled_report = result.scalar_one_or_none()

                if not scheduled_report:
                    raise ValueError(f"Scheduled report {report_id} not found")

                # Use custom dates or default based on frequency
                if not end_date:
                    end_date = datetime.now().date()
                if not start_date:
                    if scheduled_report.frequency == ReportFrequency.DAILY.value:
                        start_date = end_date - timedelta(days=1)
                    elif scheduled_report.frequency == ReportFrequency.WEEKLY.value:
                        start_date = end_date - timedelta(days=7)
                    elif scheduled_report.frequency == ReportFrequency.MONTHLY.value:
                        first_of_month = end_date.replace(day=1)
                        start_date = (first_of_month - timedelta(days=1)).replace(day=1)
                        end_date = first_of_month - timedelta(days=1)
                    else:
                        start_date = end_date - timedelta(days=7)

                # Generate report
                generator = ReportGenerator(db)
                report_bytes = await generator.generate_report(
                    clinic_id=scheduled_report.clinic_id,
                    report_type=scheduled_report.report_type,
                    start_date=start_date,
                    end_date=end_date,
                    format=scheduled_report.report_format,
                    parameters=scheduled_report.parameters or {},
                )

                return report_bytes

            finally:
                break  # Only need one iteration


# Global scheduler instance
_scheduler: Optional[ReportScheduler] = None


def get_report_scheduler() -> ReportScheduler:
    """Get global report scheduler instance."""
    global _scheduler
    if _scheduler is None:
        # TODO: Load SMTP config from settings
        _scheduler = ReportScheduler()
    return _scheduler


async def start_scheduler():
    """Start the report scheduler (called on app startup)."""
    scheduler = get_report_scheduler()
    scheduler.start()
    await scheduler.load_all_scheduled_reports()


async def stop_scheduler():
    """Stop the report scheduler (called on app shutdown)."""
    scheduler = get_report_scheduler()
    scheduler.stop()
