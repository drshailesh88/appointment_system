"""
Tests for APScheduler integration.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.scheduler import (
    init_scheduler,
    get_scheduler,
    start_scheduler,
    shutdown_scheduler,
    _job_executed_listener,
    _job_error_listener,
)
from app.core.config import settings


class TestSchedulerInitialization:
    """Tests for scheduler initialization."""

    def test_init_scheduler_creates_instance(self):
        """Test that init_scheduler creates a scheduler instance."""
        # Temporarily enable scheduler
        with patch.object(settings, 'scheduler_enabled', True):
            with patch.object(settings, 'testing', False):
                scheduler = init_scheduler()

                assert scheduler is not None
                assert isinstance(scheduler, AsyncIOScheduler)
                assert scheduler.timezone.zone == settings.scheduler_timezone

                # Clean up
                if scheduler.running:
                    scheduler.shutdown(wait=False)

    def test_init_scheduler_disabled_when_testing(self):
        """Test that scheduler is disabled when TESTING=True."""
        with patch.object(settings, 'testing', True):
            scheduler = init_scheduler()
            assert scheduler is None

    def test_init_scheduler_disabled_when_flag_false(self):
        """Test that scheduler is disabled when SCHEDULER_ENABLED=False."""
        with patch.object(settings, 'scheduler_enabled', False):
            scheduler = init_scheduler()
            assert scheduler is None

    def test_get_scheduler_returns_instance(self):
        """Test that get_scheduler returns the global instance."""
        with patch.object(settings, 'scheduler_enabled', True):
            with patch.object(settings, 'testing', False):
                scheduler = init_scheduler()
                assert get_scheduler() is scheduler

                # Clean up
                if scheduler and scheduler.running:
                    scheduler.shutdown(wait=False)


class TestSchedulerLifecycle:
    """Tests for scheduler startup and shutdown."""

    @pytest.mark.asyncio
    async def test_start_scheduler_adds_jobs(self):
        """Test that start_scheduler adds all jobs."""
        with patch.object(settings, 'scheduler_enabled', True):
            with patch.object(settings, 'testing', False):
                scheduler = init_scheduler()

                # Mock job addition functions
                with patch('app.core.scheduler.add_calendar_sync_job') as mock_calendar:
                    with patch('app.core.scheduler.add_daily_digest_job') as mock_digest:
                        with patch('app.core.scheduler.add_emr_sync_job') as mock_emr:
                            with patch('app.core.scheduler.add_reminder_job') as mock_reminder:
                                with patch('app.core.scheduler.add_insurance_job') as mock_insurance:
                                    await start_scheduler()

                                    # Verify all job functions were called
                                    mock_calendar.assert_called_once()
                                    mock_digest.assert_called_once()
                                    mock_emr.assert_called_once()
                                    mock_reminder.assert_called_once()
                                    mock_insurance.assert_called_once()

                                    # Verify scheduler is running
                                    assert scheduler.running

                # Clean up
                await shutdown_scheduler()

    @pytest.mark.asyncio
    async def test_start_scheduler_when_disabled(self):
        """Test that start_scheduler does nothing when scheduler is disabled."""
        with patch.object(settings, 'scheduler_enabled', False):
            scheduler = init_scheduler()
            assert scheduler is None

            # Should not raise any errors
            await start_scheduler()

    @pytest.mark.asyncio
    async def test_shutdown_scheduler_stops_gracefully(self):
        """Test that shutdown_scheduler stops the scheduler gracefully."""
        with patch.object(settings, 'scheduler_enabled', True):
            with patch.object(settings, 'testing', False):
                scheduler = init_scheduler()

                with patch('app.core.scheduler.add_calendar_sync_job'):
                    with patch('app.core.scheduler.add_daily_digest_job'):
                        with patch('app.core.scheduler.add_emr_sync_job'):
                            with patch('app.core.scheduler.add_reminder_job'):
                                with patch('app.core.scheduler.add_insurance_job'):
                                    await start_scheduler()
                                    assert scheduler.running

                                    await shutdown_scheduler()
                                    assert not scheduler.running


class TestJobEventListeners:
    """Tests for job event listeners."""

    def test_job_executed_listener_logs_success(self, caplog):
        """Test that job execution is logged."""
        event = Mock()
        event.job_id = 'test_job'

        with caplog.at_level('INFO'):
            _job_executed_listener(event)

        assert 'test_job' in caplog.text
        assert 'executed successfully' in caplog.text

    def test_job_error_listener_logs_error(self, caplog):
        """Test that job errors are logged."""
        event = Mock()
        event.job_id = 'test_job'
        event.exception = ValueError("Test error")

        with caplog.at_level('ERROR'):
            _job_error_listener(event)

        assert 'test_job' in caplog.text
        assert 'raised an exception' in caplog.text


class TestSchedulerJobs:
    """Tests for individual job modules."""

    @pytest.mark.asyncio
    async def test_calendar_sync_job_task(self):
        """Test calendar sync job task."""
        from app.jobs.calendar_sync_job import calendar_sync_task

        with patch('app.jobs.calendar_sync_job.get_google_calendar_integration') as mock_gcal:
            mock_integration = Mock()
            mock_integration.is_configured.return_value = True
            mock_gcal.return_value = mock_integration

            # Should not raise any errors
            await calendar_sync_task()

    @pytest.mark.asyncio
    async def test_daily_digest_job_task(self):
        """Test daily digest job task."""
        from app.jobs.daily_digest_job import daily_digest_task

        # Should not raise any errors (placeholder implementation)
        await daily_digest_task()

    @pytest.mark.asyncio
    async def test_emr_sync_job_task(self):
        """Test EMR sync job task."""
        from app.jobs.emr_sync_job import emr_sync_task

        with patch.object(settings, 'emr_sync_enabled', False):
            # Should skip when disabled
            await emr_sync_task()

    @pytest.mark.asyncio
    async def test_reminder_job_task(self):
        """Test appointment reminder job task."""
        from app.jobs.reminder_job import appointment_reminder_task

        # Should not raise any errors (placeholder implementation)
        await appointment_reminder_task()

    @pytest.mark.asyncio
    async def test_insurance_job_task(self):
        """Test insurance status check job task."""
        from app.jobs.insurance_job import insurance_status_task

        # Should not raise any errors (placeholder implementation)
        await insurance_status_task()

    def test_add_calendar_sync_job(self):
        """Test adding calendar sync job to scheduler."""
        from app.jobs.calendar_sync_job import add_calendar_sync_job

        scheduler = Mock(spec=AsyncIOScheduler)
        add_calendar_sync_job(scheduler)

        scheduler.add_job.assert_called_once()
        call_args = scheduler.add_job.call_args

        assert call_args.kwargs['id'] == 'calendar_sync'
        assert call_args.kwargs['name'] == 'Google Calendar Sync'
        assert call_args.args[1] == 'interval'

    def test_add_daily_digest_job(self):
        """Test adding daily digest job to scheduler."""
        from app.jobs.daily_digest_job import add_daily_digest_job

        scheduler = Mock(spec=AsyncIOScheduler)
        add_daily_digest_job(scheduler)

        scheduler.add_job.assert_called_once()
        call_args = scheduler.add_job.call_args

        assert call_args.kwargs['id'] == 'daily_digest'
        assert call_args.kwargs['name'] == 'Daily Digest Generation'
        assert call_args.args[1] == 'cron'

    def test_add_emr_sync_job(self):
        """Test adding EMR sync job to scheduler."""
        from app.jobs.emr_sync_job import add_emr_sync_job

        scheduler = Mock(spec=AsyncIOScheduler)
        add_emr_sync_job(scheduler)

        scheduler.add_job.assert_called_once()
        call_args = scheduler.add_job.call_args

        assert call_args.kwargs['id'] == 'emr_sync'
        assert call_args.kwargs['name'] == 'EMR Database Sync'
        assert call_args.args[1] == 'interval'

    def test_add_reminder_job(self):
        """Test adding appointment reminder job to scheduler."""
        from app.jobs.reminder_job import add_reminder_job

        scheduler = Mock(spec=AsyncIOScheduler)
        add_reminder_job(scheduler)

        scheduler.add_job.assert_called_once()
        call_args = scheduler.add_job.call_args

        assert call_args.kwargs['id'] == 'appointment_reminders'
        assert call_args.kwargs['name'] == 'Appointment Reminders'
        assert call_args.args[1] == 'interval'

    def test_add_insurance_job(self):
        """Test adding insurance status check job to scheduler."""
        from app.jobs.insurance_job import add_insurance_job

        scheduler = Mock(spec=AsyncIOScheduler)
        add_insurance_job(scheduler)

        scheduler.add_job.assert_called_once()
        call_args = scheduler.add_job.call_args

        assert call_args.kwargs['id'] == 'insurance_status'
        assert call_args.kwargs['name'] == 'Insurance Claim Status Check'
        assert call_args.args[1] == 'interval'


@pytest.mark.asyncio
class TestSchedulerAPI:
    """Tests for scheduler API endpoints."""

    async def test_get_scheduler_status(self, client):
        """Test GET /admin/scheduler/status endpoint."""
        # Mock scheduler
        with patch('app.api.v1.scheduler.get_scheduler') as mock_get:
            mock_scheduler = Mock()
            mock_scheduler.running = True
            mock_scheduler.get_jobs.return_value = [Mock(), Mock()]
            mock_scheduler.timezone = 'Asia/Kolkata'
            mock_get.return_value = mock_scheduler

            response = await async_client.get("/api/v1/admin/scheduler/status")

            assert response.status_code == 200
            data = response.json()
            assert data['running'] is True
            assert data['jobs_count'] == 2
            assert 'timezone' in data

    async def test_get_scheduler_status_when_disabled(self, client):
        """Test GET /admin/scheduler/status when scheduler is disabled."""
        with patch('app.api.v1.scheduler.get_scheduler', return_value=None):
            response = await client.get("/api/v1/admin/scheduler/status")
            assert response.status_code == 503

    async def test_list_jobs(self, client):
        """Test GET /admin/scheduler/jobs endpoint."""
        with patch('app.api.v1.scheduler.get_scheduler') as mock_get:
            mock_job = Mock()
            mock_job.id = 'test_job'
            mock_job.name = 'Test Job'
            mock_job.next_run_time = datetime.now()
            mock_job.trigger = 'interval'

            mock_scheduler = Mock()
            mock_scheduler.get_jobs.return_value = [mock_job]
            mock_get.return_value = mock_scheduler

            response = await client.get("/api/v1/admin/scheduler/jobs")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['id'] == 'test_job'
            assert data[0]['name'] == 'Test Job'

    async def test_pause_job(self, client):
        """Test POST /admin/scheduler/jobs/{job_id}/pause endpoint."""
        with patch('app.api.v1.scheduler.get_scheduler') as mock_get:
            mock_job = Mock()
            mock_scheduler = Mock()
            mock_scheduler.get_job.return_value = mock_job
            mock_get.return_value = mock_scheduler

            response = await client.post("/api/v1/admin/scheduler/jobs/test_job/pause")

            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'success'
            assert 'paused' in data['message']
            mock_scheduler.pause_job.assert_called_once_with('test_job')

    async def test_resume_job(self, client):
        """Test POST /admin/scheduler/jobs/{job_id}/resume endpoint."""
        with patch('app.api.v1.scheduler.get_scheduler') as mock_get:
            mock_job = Mock()
            mock_scheduler = Mock()
            mock_scheduler.get_job.return_value = mock_job
            mock_get.return_value = mock_scheduler

            response = await client.post("/api/v1/admin/scheduler/jobs/test_job/resume")

            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'success'
            assert 'resumed' in data['message']
            mock_scheduler.resume_job.assert_called_once_with('test_job')

    async def test_run_job_manually(self, client):
        """Test POST /admin/scheduler/jobs/{job_id}/run endpoint."""
        with patch('app.api.v1.scheduler.get_scheduler') as mock_get:
            mock_job = Mock()
            mock_scheduler = Mock()
            mock_scheduler.get_job.return_value = mock_job
            mock_scheduler.run_job.return_value = None
            mock_get.return_value = mock_scheduler

            response = await client.post("/api/v1/admin/scheduler/jobs/test_job/run")

            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'success'
            assert 'triggered' in data['message']

    async def test_pause_nonexistent_job(self, client):
        """Test pausing a job that doesn't exist."""
        with patch('app.api.v1.scheduler.get_scheduler') as mock_get:
            mock_scheduler = Mock()
            mock_scheduler.get_job.return_value = None
            mock_get.return_value = mock_scheduler

            response = await client.post("/api/v1/admin/scheduler/jobs/nonexistent/pause")

            assert response.status_code == 404
            assert 'not found' in response.json()['detail']
