from pydantic import BaseModel
from enum import Enum

class DocumentType(str, Enum):
    """Document type for uploads"""
    CV = "cv"
    PROJECT_REPORT= "project_report"


class UploadRequest(BaseModel):
    """Upload file request"""
    document_type: DocumentType

class UploadResponse(BaseModel):
    """Upload file response"""
    id: str
    filename: str
    document_type: DocumentType
    file_size: int
    uploaded_at: str
