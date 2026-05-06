# app/api/v1/routes/health.py
# ============================================================
#  /api/v1/health  — Service health check
# ============================================================

from fastapi import APIRouter
from app.schemas.travel import HealthResponse
from app.core.config import get_settings
from app.core.logging import logger

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


@router.get("/", response_model=HealthResponse, summary="Health check")
async def health_check():
    """
    Returns the health status of TravelMate backend and all configured services.
    Frontend pings this on startup to verify connectivity.
    """
    services = {
        "groq":   "configured" if settings.groq_api_key   else "missing_key",
        "gemini": "configured" if settings.gemini_api_key else "missing_key",
        "tavily": "configured" if settings.tavily_api_key else "missing_key",
    }

    overall = "ok" if all(v == "configured" for v in services.values()) else "degraded"

    return HealthResponse(
        status=overall,
        version="1.0.0",
        services=services,
    )
