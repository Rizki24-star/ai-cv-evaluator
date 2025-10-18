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
    gemini_embedding_model: str = "model/text-embedding-004"
    gemini_temperature: float = 0.2
    gemini_max_tokens: int = 2048

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
