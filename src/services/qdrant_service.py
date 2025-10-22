from config import get_settings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from typing import List, Dict, Optional
import uuid
import logging
from models.qdrant import RAGContext, ChunkMetadata

settings = get_settings()

class QdrantService:
    """Qdrant service with production-ready features"""

    def __init__(self, url: Optional[str] = None):
        """Initialize Qdrant client"""
        self.url = url or settings.qdrant_url
        self.client = QdrantClient(url=self.url)
        self.embedding_dimension = settings.qdrant_embedding_dimension
        logging.info(f"Connected to Qdrant at {self.url}")

    def create_collections(self) -> None:
        """Create collection if they dont exist"""

        collection = [
            settings.qdrant_cv_collection,
            settings.qdrant_project_collection
        ]

        for collection_name in collection:
            if not self.client.collection_exists(collection_name):
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logging.info(f"Created collection: {collection_name}")
            else:
                logging.info(f"Collection already exists: {collection_name}")

    def ingest_documents(
            self,
            collection_name: str,
            chunks: List[ChunkMetadata],
            embeddings: List[List[float]]
    ) -> int:
        """Ingest document chunks with embeddings"""

        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=chunk.model_dump()
                )
            )

        # Batch upload
        self.client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )

        logging.info(f"Ingested {len(points)} chunks to {collection_name}")
        return len(points)

    def search_with_filter(
       self,
       collection_name: str,
       query_embedding: List[float],
       source_filter: Optional[str] = None,
       top_k: int = 5,
       score_threshold: float = 0.7
    ) -> List[RAGContext]:
        """
        Search with metadata filtering
        """

        # Build filter if source specified
        search_filter = None
        if source_filter:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source_filter)
                    )
                ]
            )

        # Search
        search_result = self.client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k,
            score_threshold=score_threshold
        )

        # Convert to RAGContext
        contexts = []
        for hit in search_result:
            contexts.append(
                RAGContext(
                    content=hit.payload.get("content", ""),
                    source=hit.payload.get("source", "unknown"),
                    score=hit.score,
                    metadata=hit.payload
                )
            )

        logging.info(
            f"Retrieved {len(contexts)} chunks from {collection_name} "
            f"(source_filter: {source_filter})"
        )

        return contexts

    def get_evaluation_context(
        self,
        collection_name: str,
        query_embedding: List[float],
        separate_sources: bool = True
    ) -> Dict[str, List[RAGContext]]:
        """
        Get organized context for evaluation
        """

        if not separate_sources:
            logging.info("Start search")
            contexts = self.search_with_filter(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=settings.rag_top_k,
                score_threshold=settings.rag_score_threshold
            )
            return {"all": contexts}

        logging.debug("Pass Search")
        # Separate searches by source type
        if collection_name == settings.qdrant_cv_collection:
            sources = ["job_description", "cv_rubric"]
        else:  # project collection
            sources = ["case_study_brief", "project_rubric"]

        result = {}
        for source in sources:
            contexts = self.search_with_filter(
                collection_name=collection_name,
                query_embedding=query_embedding,
                source_filter=source,
                top_k=3,  # Fewer per source
                score_threshold=settings.rag_score_threshold
            )
            result[source] = contexts

        return result

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection (for re-ingestion)
        """
        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
            logging.info(f"Deleted collection: {collection_name}")

    def get_collection_info(self, collection_name: str) -> Dict:
        """
        Get collection statistics
        """
        if not self.client.collection_exists(collection_name):
            return {"exists": False}

        info = self.client.get_collection(collection_name)

        return {
            "exists": True,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status
        }

# Singleton instance
_qdrant_service = None


def get_qdrant_service() -> QdrantService:
    """
    Get or create QdrantService singleton
    """
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service
