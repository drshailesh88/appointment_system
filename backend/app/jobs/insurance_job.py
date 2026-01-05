"""
Insurance claim status background job.

Checks and updates insurance claim statuses.
Runs every 6 hours (configurable).
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)


async def insurance_status_task():
    """
    Check and update insurance claim statuses.

    This job:
    1. Fetches all pending insurance claims
    2. Queries TPA APIs for status updates
    3. Updates claim statuses in database
    4. Sends notifications for status changes
    """
    logger.info("Starting insurance claim status check")
    start_time = datetime.now()

    try:
        # TODO: Implement actual insurance status check
        # This will need to:
        # 1. Query all claims with status = 'pending' or 'submitted'
        # 2. For each claim:
        #    - Query TPA API for status
        #    - Update status in database
        #    - If status changed, send notification to doctor/patient
        # 3. Handle API failures and retries

        logger.info("Insurance claim status check completed")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Insurance status check took {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Insurance status check job failed: {e}", exc_info=True)
        raise


def add_insurance_job(scheduler: AsyncIOScheduler):
    """
    Add insurance status check job to the scheduler.

    Args:
        scheduler: APScheduler instance
    """
    interval_hours = settings.insurance_check_interval_hours

    scheduler.add_job(
        insurance_status_task,
        'interval',
        hours=interval_hours,
        id='insurance_status',
        name='Insurance Claim Status Check',
        replace_existing=True,
        max_instances=1
    )

    logger.info(f"Insurance status check job scheduled (every {interval_hours} hours)")
