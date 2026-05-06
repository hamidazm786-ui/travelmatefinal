# app/api/v1/routes/search.py
# ============================================================
#  /api/v1/search  — Live web search endpoints via Tavily
# ============================================================

from fastapi import APIRouter, HTTPException, Query
from app.services.search_tavily import (
    search_flights,
    search_hotels,
    search_activities,
    search_destination_overview,
    gather_all_travel_data,
)
from app.schemas.travel import SearchResultsResponse, TravelQueryRequest
from app.core.logging import logger
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: str
    budget_level: str = "moderate"
    trip_type: str    = "leisure"


@router.post("/all", summary="Search flights, hotels, and activities")
async def search_all(req: SearchRequest):
    """
    Runs all Tavily searches in parallel for a destination.
    Returns raw search context for display or further LLM processing.
    """
    try:
        data = await gather_all_travel_data(
            origin=req.origin,
            destination=req.destination,
            departure_date=req.departure_date,
            return_date=req.return_date,
            budget_level=req.budget_level,
            trip_type=req.trip_type,
        )
        return {"status": "ok", "data": data}
    except Exception as e:
        logger.error(f"[Route/search] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/destination", summary="Get destination overview")
async def destination_overview(destination: str = Query(..., description="City or country name")):
    """Quick search for destination travel guide info."""
    try:
        result = await search_destination_overview(destination)
        return {"destination": destination, "overview": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flights", summary="Search for flight options")
async def search_flight_options(
    origin: str      = Query(...),
    destination: str = Query(...),
    date: str        = Query(..., description="YYYY-MM-DD"),
):
    try:
        result = await search_flights(origin, destination, date)
        return {"origin": origin, "destination": destination, "date": date, "flights": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hotels", summary="Search for hotel options")
async def search_hotel_options(
    destination: str  = Query(...),
    check_in: str     = Query(...),
    check_out: str    = Query(...),
    budget_level: str = Query(default="moderate"),
):
    try:
        result = await search_hotels(destination, check_in, check_out, budget_level)
        return {"destination": destination, "hotels": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activities", summary="Search for activities")
async def search_activity_options(
    destination: str = Query(...),
    trip_type: str   = Query(default="leisure"),
):
    try:
        result = await search_activities(destination, trip_type)
        return {"destination": destination, "activities": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
