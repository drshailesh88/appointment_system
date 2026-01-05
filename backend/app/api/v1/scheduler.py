"""
Scheduler management API endpoints.

Provides admin endpoints to manage scheduled jobs:
- List all jobs
- Run job manually
- Pause/resume jobs
- Get scheduler status
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


class JobInfo(BaseModel):
    """Job information schema."""
    id: str
    name: str
    next_run_time: str | None
    trigger: str
    paused: bool


class SchedulerStatus(BaseModel):
    """Scheduler status schema."""
    running: bool
    jobs_count: int
    timezone: str


@router.get("/admin/scheduler/status", response_model=SchedulerStatus)
async def get_scheduler_status():
    """
    Get scheduler status.

    Returns:
        SchedulerStatus: Scheduler running state and job count
    """
    scheduler = get_scheduler()

    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    jobs_count = len(scheduler.get_jobs())

    return SchedulerStatus(
        running=scheduler.running,
        jobs_count=jobs_count,
        timezone=str(scheduler.timezone)
    )


@router.get("/admin/scheduler/jobs", response_model=List[JobInfo])
async def list_jobs():
    """
    List all scheduled jobs.

    Returns:
        List[JobInfo]: List of all scheduled jobs with their details
    """
    scheduler = get_scheduler()

    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    jobs = scheduler.get_jobs()
    job_list = []

    for job in jobs:
        job_list.append(JobInfo(
            id=job.id,
            name=job.name,
            next_run_time=str(job.next_run_time) if job.next_run_time else None,
            trigger=str(job.trigger),
            paused=job.next_run_time is None
        ))

    return job_list


@router.post("/admin/scheduler/jobs/{job_id}/run")
async def run_job_manually(job_id: str):
    """
    Run a job manually (immediately).

    Args:
        job_id: ID of the job to run

    Returns:
        Dict: Success message
    """
    scheduler = get_scheduler()

    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    try:
        job = scheduler.get_job(job_id)

        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found"
            )

        # Trigger job to run immediately by modifying next_run_time
        # Note: We can't directly call job.func() here because it's async
        # Instead, we use modify_job to set next_run_time to now
        from datetime import datetime
        scheduler.modify_job(job_id, next_run_time=datetime.now())

        logger.info(f"Job '{job_id}' triggered manually")

        return {
            "status": "success",
            "message": f"Job '{job_id}' triggered successfully",
            "job_id": job_id
        }

    except Exception as e:
        logger.error(f"Error running job '{job_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run job: {str(e)}"
        )


@router.post("/admin/scheduler/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """
    Pause a scheduled job.

    Args:
        job_id: ID of the job to pause

    Returns:
        Dict: Success message
    """
    scheduler = get_scheduler()

    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    try:
        job = scheduler.get_job(job_id)

        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found"
            )

        scheduler.pause_job(job_id)
        logger.info(f"Job '{job_id}' paused")

        return {
            "status": "success",
            "message": f"Job '{job_id}' paused successfully",
            "job_id": job_id
        }

    except Exception as e:
        logger.error(f"Error pausing job '{job_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause job: {str(e)}"
        )


@router.post("/admin/scheduler/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """
    Resume a paused job.

    Args:
        job_id: ID of the job to resume

    Returns:
        Dict: Success message
    """
    scheduler = get_scheduler()

    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    try:
        job = scheduler.get_job(job_id)

        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found"
            )

        scheduler.resume_job(job_id)
        logger.info(f"Job '{job_id}' resumed")

        return {
            "status": "success",
            "message": f"Job '{job_id}' resumed successfully",
            "job_id": job_id
        }

    except Exception as e:
        logger.error(f"Error resuming job '{job_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume job: {str(e)}"
        )
