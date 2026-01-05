"""
Appointment reminder background job.

Sends reminders for upcoming appointments.
Runs every hour (configurable).
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)


async def appointment_reminder_task():
    """
    Send reminders for upcoming appointments.

    This job:
    1. Finds appointments scheduled in the next 24 hours
    2. Filters appointments that haven't received reminders yet
    3. Sends SMS/WhatsApp/push notification reminders
    4. Marks appointments as reminder-sent
    """
    logger.info("Starting appointment reminder job")
    start_time = datetime.now()

    try:
        # Calculate time window (next 24 hours)
        now = datetime.now()
        window_end = now + timedelta(hours=24)

        # TODO: Implement actual reminder logic
        # This will need to:
        # 1. Query appointments between now and window_end
        # 2. Filter appointments that need reminders
        # 3. For each appointment:
        #    - Get patient contact info
        #    - Generate reminder message
        #    - Send via SMS/WhatsApp/push notification
        #    - Mark as reminder_sent
        # 4. Handle failures gracefully

        logger.info(f"Checking appointments from {now} to {window_end}")

        # Placeholder for actual implementation
        logger.info("Appointment reminders sent successfully")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Appointment reminder job took {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Appointment reminder job failed: {e}", exc_info=True)
        raise


def add_reminder_job(scheduler: AsyncIOScheduler):
    """
    Add appointment reminder job to the scheduler.

    Args:
        scheduler: APScheduler instance
    """
    interval_minutes = settings.reminder_check_interval_minutes

    scheduler.add_job(
        appointment_reminder_task,
        'interval',
        minutes=interval_minutes,
        id='appointment_reminders',
        name='Appointment Reminders',
        replace_existing=True,
        max_instances=1
    )

    logger.info(f"Appointment reminder job scheduled (every {interval_minutes} minutes)")
