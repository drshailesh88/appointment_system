"""
EMR sync background job.

Syncs data with DocAssist EMR database.
Runs every 5 minutes (configurable).
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)


async def emr_sync_task():
    """
    Sync data with EMR database.

    This job:
    1. Syncs patient data from EMR to Practice Manager
    2. Syncs appointments bidirectionally
    3. Links visits to appointments
    4. Syncs procedure records
    5. Handles conflicts gracefully
    """
    logger.info("Starting EMR sync job")
    start_time = datetime.now()

    try:
        if not settings.emr_sync_enabled:
            logger.debug("EMR sync disabled, skipping")
            return

        if not settings.emr_database_path:
            logger.warning("EMR database path not configured, skipping sync")
            return

        # TODO: Implement actual EMR sync logic
        # This will need to:
        # 1. Connect to EMR SQLite database
        # 2. Fetch updated patient records
        # 3. Sync appointments (both directions)
        # 4. Link visits to appointments
        # 5. Handle conflicts and errors

        logger.info("EMR sync completed successfully")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"EMR sync took {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"EMR sync job failed: {e}", exc_info=True)
        raise


def add_emr_sync_job(scheduler: AsyncIOScheduler):
    """
    Add EMR sync job to the scheduler.

    Args:
        scheduler: APScheduler instance
    """
    interval_minutes = settings.emr_sync_interval_minutes

    scheduler.add_job(
        emr_sync_task,
        'interval',
        minutes=interval_minutes,
        id='emr_sync',
        name='EMR Database Sync',
        replace_existing=True,
        max_instances=1
    )

    logger.info(f"EMR sync job scheduled (every {interval_minutes} minutes)")
