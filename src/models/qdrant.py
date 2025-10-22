from pydantic import BaseModel
from typing import Dict, Any, Optional

class RAGContext(BaseModel):
    """Retrieve context from Qdrant"""
    content: str
    source: str
    score: float
    metadata: Dict[str, Any] = {}

class ChunkMetadata(BaseModel):
    """Metadata for document chunks"""
    source: str
    content: str
    chunk_index: int
    section: Optional[str] = None
    category: Optional[str] = None
