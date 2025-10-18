from fastapi import FastAPI
from config import get_settings
from rate_limiting import limiter

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AI-powered candidate screening system that automates CV and project evaluation.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

limiter(app)

@app.get("/")
async def root():
    return {"message": "Hello World"}
