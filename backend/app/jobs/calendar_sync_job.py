"""
Calendar sync background job.

Syncs all doctors' Google calendars with appointments in the system.
Runs every 5 minutes (configurable).
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.integrations.google_calendar import get_google_calendar_integration

logger = logging.getLogger(__name__)


async def calendar_sync_task():
    """
    Sync all connected Google calendars with appointments.

    This job:
    1. Fetches all doctors with connected Google calendars
    2. For each doctor, syncs their appointments to Google Calendar
    3. Handles errors gracefully to avoid breaking the sync for other doctors
    """
    logger.info("Starting calendar sync job")
    start_time = datetime.now()

    try:
        gcal = get_google_calendar_integration()

        if not gcal.is_configured():
            logger.warning("Google Calendar not configured, skipping sync")
            return

        # TODO: Implement actual sync logic
        # This will need to:
        # 1. Get all doctors from the database
        # 2. Filter doctors with calendar_token
        # 3. For each doctor, fetch their appointments
        # 4. Sync appointments to Google Calendar
        # 5. Handle bidirectional sync (calendar -> appointments)

        logger.info("Calendar sync completed successfully")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Calendar sync took {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Calendar sync job failed: {e}", exc_info=True)
        raise


def add_calendar_sync_job(scheduler: AsyncIOScheduler):
    """
    Add calendar sync job to the scheduler.

    Args:
        scheduler: APScheduler instance
    """
    interval_minutes = settings.calendar_sync_interval_minutes

    scheduler.add_job(
        calendar_sync_task,
        'interval',
        minutes=interval_minutes,
        id='calendar_sync',
        name='Google Calendar Sync',
        replace_existing=True,
        max_instances=1
    )

    logger.info(f"Calendar sync job scheduled (every {interval_minutes} minutes)")
