from redis import asyncio as redis
import json
from typing import Optional, Dict, Any
from datetime import datetime
from config import get_settings
from models.job import JobStatus
import logging

settings = get_settings()

async def get_redis_client() -> redis.Redis:
    """
    Create a new Redis Client instance
    """
    return redis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )

async def create_job_record(
        job_id: str,
        cv_id: str,
        report_id: str,
        job_title: str,
        status: str,
        created_at: datetime
) -> None:
    """
    Create Initial Job Record in Redis
    """

    client = await get_redis_client()

    job_data = {
        "id": job_id,
        "cv_id": cv_id,
        "report_id": report_id,
        "job_title": job_title,
        "status": status.value,
        "created_at": created_at.isoformat() + "Z",
        "updated_at": created_at.isoformat() + "Z",
        "retry_count": 0
    }

    await client.setex(f"job:{job_id}", settings.redis_job_ttl, json.dumps(job_data))

    logging.info(f"Created job record: {job_id}")

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve job status and result
    """

    client = await get_redis_client()

    job_data_str = await client.get(f"job:{job_id}")

    if not job_data_str:
        return None

    return json.loads(job_data_str)

async def update_job_status(
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
) -> None:
    """
    Update job status and optionally add results
    """

    client = await get_redis_client()

    # Get existing job data
    job_data_str = await client.get(f"job:{job_id}")

    if not job_data_str:
        logging.error(f"Job not found for update: {job_id}")
        raise ValueError(f"Job {job_id} not found")

    job_data = json.loads(job_data_str)

    # Update fields
    job_data["status"] = status.value
    job_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

    if result:
        # Merge evaluation results
        job_data.update(result)

    if error:
        job_data["error"] = error

    if status == JobStatus.COMPLETED:
        job_data["completed_at"] = datetime.utcnow().isoformat() + "Z"

    if status == JobStatus.RETRYING:
        job_data["retry_count"] = job_data.get("retry_count", 0) + 1


    await client.setex(
        f"job:{job_id}",
        settings.redis_job_ttl,
        json.dumps(job_data)
    )

    logging.info(f"Updated job {job_id}: status={status.value}")
