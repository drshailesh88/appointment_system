"""
Background Calendar Sync Service.

Periodically syncs appointments to Google Calendar using APScheduler.
"""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.calendar_settings import DoctorCalendarSettings
from app.services.calendar_sync import CalendarSyncService

logger = logging.getLogger(__name__)


class BackgroundCalendarSyncService:
    """
    Background service for periodic calendar synchronization.

    Runs a scheduled job every 15 minutes to sync appointments to Google Calendar.
    """

    def __init__(self):
        """Initialize background sync service."""
        self.scheduler = AsyncIOScheduler()
        self._running = False

        # Database setup
        self.engine = create_async_engine(
            settings.async_database_url,
            echo=False,
            pool_pre_ping=True,
        )
        self.async_session_maker = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def _sync_all_doctors(self):
        """Sync appointments for all doctors with calendar enabled."""
        async with self.async_session_maker() as db:
            try:
                # Get all doctors with calendar sync enabled
                result = await db.execute(
                    select(DoctorCalendarSettings).where(
                        DoctorCalendarSettings.sync_enabled == True
                    )
                )
                settings_list = result.scalars().all()

                logger.info(f"Starting background sync for {len(settings_list)} doctors")

                total_synced = 0
                total_failed = 0

                for settings in settings_list:
                    try:
                        # Create sync service
                        sync_service = CalendarSyncService(db)

                        # Sync appointments modified since last sync
                        since = settings.last_synced_at
                        stats = await sync_service.sync_multiple_appointments(
                            doctor_id=settings.doctor_id,
                            since=since,
                        )

                        total_synced += stats.get("synced", 0)
                        total_failed += stats.get("failed", 0)

                        logger.info(
                            f"Doctor {settings.doctor_id}: "
                            f"synced={stats.get('synced', 0)}, "
                            f"failed={stats.get('failed', 0)}"
                        )

                    except Exception as e:
                        logger.error(
                            f"Error syncing doctor {settings.doctor_id}: {e}",
                            exc_info=True,
                        )
                        total_failed += 1

                logger.info(
                    f"Background sync completed: "
                    f"total_synced={total_synced}, "
                    f"total_failed={total_failed}"
                )

            except Exception as e:
                logger.error(f"Error in background sync job: {e}", exc_info=True)

    def start(self, interval_minutes: int = 15):
        """
        Start the background sync scheduler.

        Args:
            interval_minutes: How often to run sync (default: 15 minutes)
        """
        if self._running:
            logger.warning("Background sync already running")
            return

        # Add job to scheduler
        self.scheduler.add_job(
            self._sync_all_doctors,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="calendar_sync_job",
            name="Google Calendar Sync",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Start scheduler
        self.scheduler.start()
        self._running = True

        logger.info(
            f"Background calendar sync started (interval: {interval_minutes} minutes)"
        )

    def stop(self):
        """Stop the background sync scheduler."""
        if not self._running:
            return

        self.scheduler.shutdown(wait=True)
        self._running = False

        logger.info("Background calendar sync stopped")

    async def trigger_manual_sync(self):
        """Trigger a manual sync immediately."""
        logger.info("Manual sync triggered")
        await self._sync_all_doctors()


# Singleton instance
_background_sync_service: BackgroundCalendarSyncService | None = None


def get_background_sync_service() -> BackgroundCalendarSyncService:
    """Get singleton background sync service instance."""
    global _background_sync_service
    if _background_sync_service is None:
        _background_sync_service = BackgroundCalendarSyncService()
    return _background_sync_service


async def start_background_sync(interval_minutes: int = 15):
    """
    Start background calendar sync.

    Args:
        interval_minutes: How often to sync (default: 15 minutes)
    """
    service = get_background_sync_service()
    service.start(interval_minutes)


async def stop_background_sync():
    """Stop background calendar sync."""
    service = get_background_sync_service()
    service.stop()
