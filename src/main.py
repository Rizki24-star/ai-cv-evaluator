from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from config import get_settings
from api import upload, evaluate
from custom_logging import configure_logging, LogLevels
from utils.response import create_response

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

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

    from services.qdrant_service import get_qdrant_service

    try:
        qdrant  = get_qdrant_service()
        cv_info = qdrant.get_collection_info(settings.qdrant_cv_collection)
        project_info = qdrant.get_collection_info(settings.qdrant_project_collection)

        return {
            "status": "healthy",
            "services": {
                "api": "up",
                "qdrant": "up",
                "redis": "up"
            },
            "collections": {
                "cv_evaluation": cv_info,        # ← Shows collection stats
                "project_evaluation": project_info
            }
        }
    except HTTPException as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
