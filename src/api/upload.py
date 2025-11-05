from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from src.config import get_settings
from src.models.upload import DocumentType, UploadRequest, UploadResponse
from src.utils.response import create_response
import uuid
import aiofiles
from datetime import datetime
import logging

settings = get_settings()
router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...)
):
    """
    Upload CV or Project Report
    """
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )

        content = await file.read()
        file_size = len(content)

        # Check file size
        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size to large: Maximum size {settings.max_file_size}"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )

        # Generate unique ID
        doc_id = str(uuid.uuid4())

        # Create filename with document type prefix
        safe_filename = f"{document_type.value}_{doc_id}.pdf"
        file_path = settings.upload_dir / safe_filename

        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)


        logging.info(f"Uploaded {document_type.value}: {file.filename} "
                    f"({file_size} bytes) as {doc_id}")

        data = UploadResponse(
            id=doc_id,
            filename=safe_filename,
            document_type=document_type,
            file_size=file_size,
            uploaded_at=datetime.utcnow().isoformat() + "Z"
        )

        return create_response(True, "File uploaded successfully", data)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Upload file failed: {str(e)}")
        raise HTTPException(
            status_code= 500,
            detail=f"Upload file failed: {str(e)}"
        )

async def validate_document_exists(doc_id: str, doc_type: DocumentType) -> bool:
    """
    Check if document exists
    """
    filename = f"{doc_type.value}_{doc_id}.pdf"
    file_path = settings.upload_dir / filename
    return file_path.exists()
