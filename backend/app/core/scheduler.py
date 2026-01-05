"""
APScheduler configuration and initialization.

Manages background job scheduling for:
- Calendar sync
- Daily digest generation
- EMR sync
- Appointment reminders
- Insurance claim status updates
"""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance."""
    return _scheduler


def init_scheduler() -> AsyncIOScheduler:
    """
    Initialize the APScheduler with appropriate configuration.

    Returns:
        AsyncIOScheduler: Configured scheduler instance
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already initialized")
        return _scheduler

    # Check if scheduler is disabled or in testing mode
    if not settings.scheduler_enabled or settings.testing:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=False or TESTING=True)")
        return None

    # Configure job stores
    jobstores = {
        'default': MemoryJobStore()
    }

    # Configure executors
    executors = {
        'default': AsyncIOExecutor()
    }

    # Job defaults
    job_defaults = {
        'coalesce': True,  # Combine missed runs into one
        'max_instances': 1,  # Only one instance of each job at a time
        'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
    }

    # Create scheduler
    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=settings.scheduler_timezone
    )

    # Add event listeners for logging
    _scheduler.add_listener(
        _job_executed_listener,
        EVENT_JOB_EXECUTED
    )
    _scheduler.add_listener(
        _job_error_listener,
        EVENT_JOB_ERROR
    )

    logger.info(f"Scheduler initialized (timezone: {settings.scheduler_timezone})")

    return _scheduler


def _job_executed_listener(event):
    """Log successful job execution."""
    logger.info(f"Job {event.job_id} executed successfully")


def _job_error_listener(event):
    """Log job execution errors."""
    logger.error(
        f"Job {event.job_id} raised an exception: {event.exception}",
        exc_info=True
    )


async def start_scheduler():
    """Start the scheduler and add all jobs."""
    scheduler = get_scheduler()

    if scheduler is None:
        logger.info("Scheduler not initialized, skipping start")
        return

    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    # Import job modules
    from app.jobs.calendar_sync_job import add_calendar_sync_job
    from app.jobs.daily_digest_job import add_daily_digest_job
    from app.jobs.emr_sync_job import add_emr_sync_job
    from app.jobs.reminder_job import add_reminder_job
    from app.jobs.insurance_job import add_insurance_job

    # Add all jobs
    try:
        add_calendar_sync_job(scheduler)
        add_daily_digest_job(scheduler)
        add_emr_sync_job(scheduler)
        add_reminder_job(scheduler)
        add_insurance_job(scheduler)

        logger.info("All jobs added to scheduler")
    except Exception as e:
        logger.error(f"Error adding jobs to scheduler: {e}", exc_info=True)
        raise

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started successfully")


async def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global _scheduler

    if _scheduler is None:
        logger.info("Scheduler not initialized, skipping shutdown")
        return

    if not _scheduler.running:
        logger.info("Scheduler not running, skipping shutdown")
        return

    logger.info("Shutting down scheduler...")

    # Shutdown with wait for running jobs to complete
    _scheduler.shutdown(wait=True)

    _scheduler = None
    logger.info("Scheduler shut down successfully")
