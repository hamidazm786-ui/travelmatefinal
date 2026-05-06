# app/api/v1/routes/travel.py
# ============================================================
#  /api/v1/travel  — Travel plan generation endpoints
# ============================================================

from fastapi import APIRouter, HTTPException
from app.schemas.travel import TravelQueryRequest, TravelPlanResponse
from app.services.travel_planner import generate_travel_plan
from app.core.logging import logger

router = APIRouter(prefix="/travel", tags=["Travel Plan"])


@router.post("/plan", response_model=TravelPlanResponse, summary="Generate a complete travel plan")
async def create_travel_plan(query: TravelQueryRequest):
    """
    Submit travel details and receive a fully AI-generated itinerary.

    - Searches the web for live flights, hotels, and activities via Tavily
    - Generates a day-by-day plan using Groq LLM (Gemini as fallback)
    - Returns structured JSON the frontend can render immediately
    """
    try:
        logger.info(f"[Route/travel] Plan request: {query.origin} → {query.destination}")
        plan = await generate_travel_plan(query)
        return plan
    except Exception as e:
        logger.error(f"[Route/travel] Plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
