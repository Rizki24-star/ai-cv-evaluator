from redis import asyncio as redis
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.config import get_settings
from src.models.job import JobStatus
import logging

settings = get_settings()

# Utility: recursively remove keys with None values from dicts/lists
# Keeps stored job payloads clean and avoids leaking null legacy fields

def _strip_none(obj):
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if v is None:
                continue
            vv = _strip_none(v)
            clean[k] = vv
        return clean
    if isinstance(obj, list):
        return [_strip_none(v) for v in obj if v is not None]
    return obj

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
        cv_context: List[int],
        report_id: str,
        project_context: List[int],
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
        "cv_context": cv_context,
        "report_id": report_id,
        "project_context": project_context,
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

    data = json.loads(job_data_str)
    # Strip None values on read to avoid leaking null legacy fields
    return _strip_none(data)

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
