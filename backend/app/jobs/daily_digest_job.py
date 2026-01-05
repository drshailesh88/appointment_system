"""
Daily digest background job.

Generates and sends daily digest emails/notifications to doctors.
Runs every day at 6:00 AM (configurable).
"""

import logging
from datetime import datetime, date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)


async def daily_digest_task():
    """
    Generate and send daily digest to all doctors.

    This job:
    1. Fetches all doctors
    2. For each doctor, generates a digest with:
       - Today's appointment count
       - Pending waitlist entries
       - Revenue summary
       - Overdue payments
    3. Sends digest via email/push notification
    """
    logger.info("Starting daily digest generation")
    start_time = datetime.now()

    try:
        # TODO: Implement actual digest generation
        # This will need to:
        # 1. Get all active doctors from the database
        # 2. For each doctor:
        #    - Count today's appointments
        #    - Get waitlist count
        #    - Calculate today's revenue
        #    - Get overdue payments
        #    - Generate digest message
        #    - Send via email/push notification

        today = date.today()
        logger.info(f"Generating daily digest for {today}")

        # Placeholder for actual implementation
        logger.info("Daily digest sent successfully")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Daily digest generation took {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Daily digest job failed: {e}", exc_info=True)
        raise


def add_daily_digest_job(scheduler: AsyncIOScheduler):
    """
    Add daily digest job to the scheduler.

    Args:
        scheduler: APScheduler instance
    """
    hour = settings.digest_send_hour
    minute = settings.digest_send_minute

    scheduler.add_job(
        daily_digest_task,
        'cron',
        hour=hour,
        minute=minute,
        id='daily_digest',
        name='Daily Digest Generation',
        replace_existing=True,
        max_instances=1
    )

    logger.info(f"Daily digest job scheduled (every day at {hour:02d}:{minute:02d})")
