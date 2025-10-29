from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
from typing import Optional, Callable

from ..core.config import settings

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for managing scheduled tasks"""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None

    def init_scheduler(self):
        """Initialize the APScheduler"""
        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled in configuration")
            return

        self.scheduler = AsyncIOScheduler()
        logger.info("Scheduler initialized")

    def start_scheduler(self):
        """Start the scheduler"""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown_scheduler(self):
        """Shutdown the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown")

    def add_monthly_folders_job(self, func: Callable):
        """
        Add monthly folders creation job

        Args:
            func: Function to execute monthly
        """
        if not self.scheduler:
            logger.warning("Scheduler not initialized, cannot add monthly folders job")
            return

        try:
            # Parse cron expression from settings
            cron_parts = settings.scheduler_cron.split()
            if len(cron_parts) != 5:
                logger.error(f"Invalid cron expression: {settings.scheduler_cron}")
                return

            minute, hour, day, month, day_of_week = cron_parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )

            self.scheduler.add_job(
                func,
                trigger=trigger,
                id="monthly_folders",
                name="Create Monthly Folders",
                replace_existing=True
            )

            logger.info(f"Monthly folders job added with cron: {settings.scheduler_cron}")

        except Exception as e:
            logger.error(f"Failed to add monthly folders job: {e}")

    def add_backup_job(self, func: Callable, cron_expression: str = "0 2 * * 0"):
        """
        Add automated backup job

        Args:
            func: Backup function to execute
            cron_expression: Cron expression for backup schedule (default: weekly on Sunday at 2 AM)
        """
        if not self.scheduler:
            logger.warning("Scheduler not initialized, cannot add backup job")
            return

        try:
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                logger.error(f"Invalid cron expression: {cron_expression}")
                return

            minute, hour, day, month, day_of_week = cron_parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )

            self.scheduler.add_job(
                func,
                trigger=trigger,
                id="automated_backup",
                name="Automated System Backup",
                replace_existing=True
            )

            logger.info(f"Automated backup job added with cron: {cron_expression}")

        except Exception as e:
            logger.error(f"Failed to add backup job: {e}")

    def add_custom_job(
        self,
        job_id: str,
        func: Callable,
        cron_expression: str,
        job_name: Optional[str] = None
    ):
        """
        Add a custom scheduled job

        Args:
            job_id: Unique job identifier
            func: Function to execute
            cron_expression: Cron expression for schedule
            job_name: Human-readable job name
        """
        if not self.scheduler:
            logger.warning("Scheduler not initialized, cannot add custom job")
            return

        try:
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                logger.error(f"Invalid cron expression: {cron_expression}")
                return

            minute, hour, day, month, day_of_week = cron_parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )

            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=job_name or job_id,
                replace_existing=True
            )

            logger.info(f"Custom job '{job_id}' added with cron: {cron_expression}")

        except Exception as e:
            logger.error(f"Failed to add custom job '{job_id}': {e}")

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job

        Args:
            job_id: Job identifier to remove

        Returns:
            True if job was removed, False otherwise
        """
        if not self.scheduler:
            return False

        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Job '{job_id}' removed")
                return True
            else:
                logger.warning(f"Job '{job_id}' not found")
                return False
        except Exception as e:
            logger.error(f"Failed to remove job '{job_id}': {e}")
            return False

    def list_jobs(self) -> list:
        """
        List all scheduled jobs

        Returns:
            List of job information
        """
        if not self.scheduler:
            return []

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })

        return jobs

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.scheduler is not None and self.scheduler.running

# Global scheduler service instance
scheduler_service = SchedulerService()
