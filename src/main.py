import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy.sql.annotation import Annotated

from src.config import get_settings
from src.api import upload, evaluate
from src.custom_logging import configure_logging, LogLevels
from src.databases.postgres.database import sessionLocal
from src.utils.response import create_response
import src.databases.postgres.model as models
from src.databases.postgres.database import engine

settings = get_settings()
configure_logging(LogLevels.debug)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AI-powered candidate screening system that automates CV and project evaluation.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Generate all table
models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def on_startup() -> None:
    """Initialize Qdrant collections from DB categories when app starts."""
    from src.services.qdrant_service import get_qdrant_service

    logging.info("App startup: ensuring Qdrant collections exist")
    db: Session = sessionLocal()
    try:
        qdrant = get_qdrant_service()
        qdrant.create_collections(db=db)
    except Exception as e:
        logging.error(f"Failed to create Qdrant collections on startup: {e}")
        raise
    finally:
        db.close()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content=create_response(False, "Request invalid", None, {"detail": exc.errors()})
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=create_response(False, exc.detail, None, None)
    )

app.include_router(upload.router, tags=["Upload"], prefix="/api/v1")
app.include_router(evaluate.router, tags=["Evaluate"], prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "AI CV Screening Server running..."}

@app.get("/health", tags=["Health"])
async def health_check():
    """Health Check Endpoint"""
    try:
        # qdrant  = get_qdrant_service()
        return {
            "status": "healthy",
            "services": {
                "api": "up",
                "qdrant": "up",
                "redis": "up"
            },
        }
    except HTTPException as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
