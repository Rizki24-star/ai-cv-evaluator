from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded
from config import get_settings
from models.job import JobStatus
from databases.redis import update_job_status
from services.evaluation_pipeline_service import get_evaluation_pipeline
from custom_logging import LOG_FORMAT_DEBUG
import logging
import asyncio


settings = get_settings()

celery_app  = Celery(
    'tasks',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer = 'json',
    accept_content = ['json'],
    result_serializer = 'json',
    timezone = 'UTC',
    enable_utc = True,
    task_time_limit = settings.celery_task_time_limit,
    task_soft_time_limit = settings.celery_task_soft_time_limit,
    task_acks_late = True,
    worker_prefetch_multiplier = 1,
    task_track_standard=True,
    worker_log_level='DEBUG',
    worker_log_format=LOG_FORMAT_DEBUG,
    worker_task_log_format=LOG_FORMAT_DEBUG
)

@celery_app.task(bind=True, max_retries=3)
def run_evaluation_pipeline(
    self: Task,
    job_id: str,
    cv_id: str,
    report_id: str,
    job_title: str
):
    async def _run_task():
        try:
            logging.info(f"[Job {job_id}] Starting evaluation")
            await update_job_status(job_id, JobStatus.PROCESSING)

            pipeline = get_evaluation_pipeline()
            result = await pipeline.evaluate(
                cv_id=cv_id,
                report_id=report_id,
                job_title=job_title
            )

            logging.info(f"[Job {job_id}] Evaluation completed successfully")
            await update_job_status(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                result=result
            )

            return result

        except SoftTimeLimitExceeded:
            logging.error(f"[Job {job_id}] Task exceeded time limit")
            await update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error="Evaluation timed out after 4 minutes"
            )
            raise

        except Exception as e:
            logging.error(f"[Job {job_id}] Task failed: {str(e)}", exc_info=True)

            if self.request.retries < self.max_retries:
                retry_delay = 2 ** self.request.retries
                logging.info(
                    f"[Job {job_id}] Retrying in {retry_delay} seconds "
                    f"(attempt {self.request.retries + 1}/{self.max_retries})"
                )

                await update_job_status(
                    job_id=job_id,
                    status=JobStatus.RETRYING,
                    error=f"Retry {self.request.retries + 1}: {str(e)}"
                )

                raise self.retry(exc=e, countdown=retry_delay)
            else:
                logging.error(f"[Job {job_id}] Max retries reached, marking as failed")
                await update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error=f"Failed after {self.max_retries} retries: {str(e)}"
                )
                raise

    return asyncio.run(_run_task())
