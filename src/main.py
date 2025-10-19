from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from config import get_settings
from api import upload
from custom_logging import configure_logging, LogLevels
from utils.response import create_response

settings = get_settings()
configure_logging(LogLevels.info)

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



@app.get("/")
async def root():
    return {"message": "Hello World"}
