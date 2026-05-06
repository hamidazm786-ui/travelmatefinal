# main.py
# ============================================================
#  TravelMate Backend — FastAPI Application Entry Point
#  Run with: uvicorn main:app --reload --port 8000
# ============================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import get_settings
from app.core.logging import logger
from app.api.v1.router import api_router
from app.db.database import create_tables
from app.models import models  # noqa: F401 ensures ORM models are imported before table creation

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("TravelMate Backend starting up")
    logger.info(f"Environment : {settings.app_env}")
    logger.info(f"Listening on: {settings.app_host}:{settings.app_port}")
    logger.info(f"CORS origins: {settings.cors_origins}")
    logger.info(f"Groq model  : {settings.groq_model}")
    logger.info(f"Gemini model: {settings.gemini_model}")
    logger.info(f"Database URL : {settings.database_url}")
    logger.info("=" * 50)
    await create_tables()
    logger.info("Database tables ready")
    yield
    logger.info("TravelMate Backend shutting down")

# ── App Initialization ───────────────────────────────────────
app = FastAPI(
    title="TravelMate AI Backend",
    description="""
AI-powered travel planning API.
- **Groq** (llama3-70b) as primary LLM — free & fast
- **Google Gemini** as automatic fallback
- **Tavily** for live web search (flights, hotels, activities)
- File upload & analysis (PDF, DOCX, TXT)
- Conversational chat with session memory
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS — Allow frontend dev server ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Timing Middleware ───────────────────────────────
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{duration}ms"
    return response

# ── Global Exception Handler ────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )

# ── Mount all API routes ─────────────────────────────────────
app.include_router(api_router)

# ── Root endpoint ────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "TravelMate AI Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health/",
    }
