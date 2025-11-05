from fastapi import APIRouter, HTTPException, Path, Depends
from sqlalchemy.orm import Session
from src.task import run_evaluation_pipeline
from src.models.evaluate import EvaluateRequest, EvaluateResponse, EvaluationResultResponse
from src.models.upload import DocumentType
from src.models.job import JobStatus
from src.api.upload import validate_document_exists
from src.databases.redis import create_job_record, get_job_status
import logging
import uuid
from datetime import datetime

from src.databases.postgres.database import get_db
from src.repository.role_repository import find_role_by_name

router = APIRouter()

@router.post("/evaluate")
async def evaluate_candidate(request: EvaluateRequest):
    """
    Get Evaluation Result and Status
    """
    try:
        cv_exists = await validate_document_exists(request.cv_id, DocumentType.CV)
        if not cv_exists:
            raise HTTPException(
                status_code=404,
                detail=f"CV not found: {request.cv_id}"
            )

        report_exist = await validate_document_exists(request.report_id, DocumentType.PROJECT_REPORT)
        if not report_exist:
            raise HTTPException(
                status_code=404,
                detail=f"Project report not found: {request.report_id}"
            )

        # Generate Job ID
        job_id = str(uuid.uuid4())

        # Create job record (queued)
        await create_job_record(
            job_id=job_id,
            cv_id=request.cv_id,
            cv_context=request.cv_context,
            report_id=request.report_id,
            project_context=request.project_context,
            job_title=request.job_title,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        # Queue the background task (non-blocking)
        run_evaluation_pipeline.delay(
            job_id=job_id,
            cv_id=request.cv_id,
            cv_context=request.cv_context,
            report_id=request.report_id,
            project_context=request.project_context,
            job_title=request.job_title
        )

        logging.info(
            f"Evaluation queued: job_id={job_id}, "
            f"cv={request.cv_id}, report={request.report_id}"
        )


        return EvaluateResponse(
            id=job_id,
            status=JobStatus.QUEUED
        )
    except HTTPException:
        raise
    except HTTPException as e:
        logging.error(f"Failed to get result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve result: {str(e)}"
        )

@router.get("/result/{job_id}", response_model=EvaluationResultResponse, response_model_exclude_none=True)
async def get_evalutation_result(
    job_id: str = Path(..., description="Job ID from /evaluate endpoint")
):
    """Get evaluation status and result"""

    try:
        job_data = await get_job_status(job_id)

        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job not found: {job_id}"
            )

        return EvaluationResultResponse(**job_data)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to get result : str{e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve result: {str(e)}")

@router.get("/role/{name}")
async def get_role(db: Session = Depends(get_db), name: str = Path(...)):
    try:
        role = find_role_by_name(db, name)
        if not role:
            raise HTTPException(
                status_code=404,
                detail=f"Role not found: {name}"
            )

        return role
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to get role: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve role: {str(e)}")