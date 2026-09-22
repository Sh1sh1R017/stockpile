"""Job queue and worker execution pool for AI B-Roll Autopilot."""

import asyncio
import logging
from typing import Callable, Optional, Dict, Any

from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.core.job import Job, JobState

logger = logging.getLogger(__name__)


class JobQueue:
    """In-memory async queue backed by persistent SQLite database."""

    def __init__(self, db: Database, max_concurrent: int = 1):
        self.db = db
        self.max_concurrent = max_concurrent
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self, handler: Callable[[Job], Any]):
        """Start the worker loop to process enqueued jobs."""
        self._is_running = True
        logger.info(f"JobQueue started (concurrency={self.max_concurrent})")

        # Resume any QUEUED or INGESTING jobs from the database
        pending_jobs = self.db.list_jobs(limit=100, status=JobState.QUEUED.value)
        for job in pending_jobs:
            logger.info(f"Resuming pending job {job.job_id} from database")
            await self._queue.put(job.job_id)

        # Start worker loops
        self._worker_task = asyncio.create_task(self._worker_loop(handler))

    async def stop(self):
        """Stop the worker loop gracefully."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("JobQueue stopped")

    async def enqueue(self, job: Job) -> str:
        """Enqueue a new job for processing."""
        self.db.save_job(job)
        self.db.record_transition(job.job_id, "NONE", job.status.value, "Job enqueued")
        await self._queue.put(job.job_id)
        logger.info(f"Job {job.job_id} enqueued for processing: {job.source_filename}")
        return job.job_id

    async def _worker_loop(self, handler: Callable[[Job], Any]):
        while self._is_running:
            try:
                job_id = await self._queue.get()
                job = self.db.get_job(job_id)
                if not job:
                    self._queue.task_done()
                    continue

                if job.status in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
                    self._queue.task_done()
                    continue

                logger.info(f"Starting execution of job {job.job_id}")
                try:
                    await handler(job)
                except Exception as e:
                    logger.error(f"Error handling job {job.job_id}: {e}", exc_info=True)
                    job.transition_to(JobState.FAILED, error=str(e))
                    self.db.save_job(job)
                    self.db.record_transition(job.job_id, job.status.value, JobState.FAILED.value, str(e))
                finally:
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)
