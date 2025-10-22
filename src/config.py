from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):

    # App Setting
    app_name: str = "AI CV Screening API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Gemini Setting
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/text-embedding-004"
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 8192

    # Qdrant Vector DB Setting
    qdrant_url: str = "http://localhost:6333"
    qdrant_cv_collection: str = "cv_evaluation_context"
    qdrant_project_collection: str = "project_evaluation_context"
    qdrant_embedding_dimension: int = 768

    # Redis Setting
    redis_url: str = "redis://localhost:6379/0"
    redis_job_ttl: int = 86400

    # File upload Setting
    upload_dir: Path =  Path("upload")
    max_file_size: int = 10 * 1024 * 1024
    allowed_extension: list= [".pdf"]

    # Celery Task Queue
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_time_limit: int = 300
    celery_task_soft_time_limit: int = 240

    # Reference Documents Settings
    reference_docs_dir: Path = Path("src/assets/reference_docs")
    job_description_file: str = "job_description.pdf"
    case_study_file: str = "case_study_brief.pdf"
    cv_rubric_file: str = "cv_scoring_rubric.pdf"
    project_rubric_file: str = "project_scoring_rubric.pdf"

    # RAG Chunking Strategy
    chunk_size: int = 500
    chunk_overlap: int = 50

    # RAG Retrieval Settings
    rag_top_k: int = 5
    rag_score_threshold: float = 0.0

    # Retry Logic Settings
    max_retries: int = 3
    retry_min_wait: int = 2
    retry_max_wait: int = 30

    # Celery Task Queue Settings
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_time_limit: int = 300
    celery_task_soft_time_limit: int = 240

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

def get_settings() -> Settings:
    return Settings()

settings = get_settings()
settings.upload_dir.mkdir(exist_ok=True, parents=True)

(settings.upload_dir / ".gitkeep").touch(exist_ok=True)
