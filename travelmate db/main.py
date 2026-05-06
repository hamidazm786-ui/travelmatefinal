# main.py
# ============================================================
#  TravelMate FastAPI Application Entry Point
#  Start: uvicorn main:app --reload --port 8000
# ============================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import create_tables
from app.api.v1.router import api_router

settings = get_settings()
logger = logging.getLogger("travelmate")


# ── Lifespan: startup + shutdown ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup: create all DB tables if they don't exist.
    On shutdown: nothing needed (asyncpg cleans itself up).
    """
    logger.info("TravelMate starting up...")
    logger.info(f"Environment : {settings.app_env}")
    logger.info(f"Database    : {settings.database_url[:40]}...")
    logger.info(f"Groq model  : {settings.groq_model}")

    # Create tables (safe to call every startup — skips existing tables)
    await create_tables()
    logger.info("Database tables ready")
    logger.info("TravelMate is ready")

    yield

    logger.info("TravelMate shutting down")


# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="TravelMate API",
    description=(
        "AI-powered travel planner with full PostgreSQL persistence.\n\n"
        "Features:\n"
        "- User registration & JWT authentication\n"
        "- Travel plan generation (Groq / Gemini LLMs)\n"
        "- Persistent chat history per user\n"
        "- Saved itineraries with full CRUD\n"
        "- Web search via Tavily"
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────
app.include_router(api_router)


# ── Health check ─────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "env": settings.app_env,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "TravelMate API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# ── Dev server ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level="info",
    )
