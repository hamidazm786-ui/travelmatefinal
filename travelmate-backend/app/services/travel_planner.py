# app/services/travel_planner.py
# ============================================================
#  Travel Planner Service — Core business logic
#  Orchestrates: Tavily search → LLM plan generation → parsing
# ============================================================

import json
import re
from typing import Dict, List, Optional, Tuple
from app.schemas.travel import (
    TravelQueryRequest, TravelPlanResponse,
    FlightResult, HotelResult, ActivityResult, DayPlan,
)
from app.services.search_tavily import gather_all_travel_data
from app.services.llm_router import route_llm
from app.core.logging import logger
from datetime import datetime, timedelta


async def generate_travel_plan(query: TravelQueryRequest) -> TravelPlanResponse:
    """
    Main entry point for travel plan generation.
    Steps:
      1. Search web with Tavily for live data
      2. Build a rich LLM prompt injecting search results
      3. Call LLM via router (Groq → Gemini fallback)
      4. Parse the JSON response into typed Pydantic models
    """
    logger.info(f"[Planner] Starting plan: {query.origin} → {query.destination}")

    # ── Step 1: Gather live search data ─────────────────────
    search_data = await gather_all_travel_data(
        origin=query.origin,
        destination=query.destination,
        departure_date=query.departure_date,
        return_date=query.return_date,
        budget_level=query.budget_level.value,
        trip_type=query.trip_type.value,
    )

    search_context = "\n\n".join(search_data.values())
    search_sources = _extract_sources(search_data)

    # ── Step 2: Calculate trip duration ─────────────────────
    try:
        dep = datetime.strptime(query.departure_date, "%Y-%m-%d")
        ret = datetime.strptime(query.return_date, "%Y-%m-%d")
        duration_days = max(1, (ret - dep).days)
    except ValueError:
        duration_days = 7

    # ── Step 3: Build and send LLM prompt ───────────────────
    system_prompt = _build_system_prompt()
    user_prompt   = _build_user_prompt(query, duration_days, search_context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    raw_response, llm_used = await route_llm(messages, temperature=0.4, max_tokens=4096)
    logger.info(f"[Planner] LLM response received via {llm_used}")

    # ── Step 4: Parse JSON from LLM response ────────────────
    plan_data = _parse_json_response(raw_response)

    return _build_response(query, plan_data, duration_days, llm_used, search_sources)


def _build_system_prompt() -> str:
    return """You are TravelMate AI, an expert travel planner with deep knowledge of global destinations, airlines, hotels, and local attractions.

Your job is to create detailed, realistic, budget-aware travel itineraries.

RULES:
- Always stay within the user's budget
- Provide specific, real hotel names and airlines when possible
- Give realistic price estimates in USD
- Create day-by-day plans that feel achievable and enjoyable
- Tailor recommendations to the trip type (leisure, adventure, business, etc.)
- ALWAYS respond with ONLY valid JSON — no explanations, no markdown, just JSON."""


def _build_user_prompt(query: TravelQueryRequest, duration_days: int, search_context: str) -> str:
    return f"""Create a complete {duration_days}-day travel plan:

TRIP DETAILS:
- From: {query.origin}
- To: {query.destination}
- Departure: {query.departure_date}
- Return: {query.return_date}
- Duration: {duration_days} days
- Travelers: {query.travelers} person(s)
- Total Budget: ${query.budget_usd} USD
- Budget Style: {query.budget_level.value}
- Trip Type: {query.trip_type.value}
- Special Notes: {query.extra_notes or "None"}

CRITICAL REQUIREMENTS FOR THE RESPONSE:
✓ FLIGHTS: Return 2-3 DIFFERENT flights with different times/airlines (REQUIRED)
✓ HOTELS: Return 3-5 COMPLETELY DIFFERENT hotels with varied price points and locations (NO DUPLICATES!)
✓ ACTIVITIES: Return 5-8 DIVERSE activities covering multiple categories:
  - Sightseeing/landmarks
  - Food & dining
  - Nature/outdoor activities
  - Culture/museums
  - Shopping/local markets
  - Entertainment/nightlife
  These MUST be specific to {query.destination} and vary in price and type!
✓ DAY-BY-DAY: Create realistic day plans with morning/afternoon/evening activities
✓ Always include TIPS section with 3+ practical travel tips

LIVE DATA FROM WEB (use this to inform your recommendations):
{search_context}

Return ONLY this JSON (no other text):
{{
  "summary": "2-3 sentence engaging overview of this trip",
  "highlights": ["highlight 1", "highlight 2", "highlight 3", "highlight 4", "highlight 5"],
  "flights": [
    {{"airline": "name", "route": "ORIGIN → DEST", "estimated_price_usd": 350.0, "duration": "6h 30m", "notes": "Book 3 weeks ahead"}}
  ],
  "hotels": [
    {{"name": "Hotel Name", "location": "District, City", "price_per_night_usd": 80.0, "rating": 4.2, "amenities": ["WiFi", "Breakfast"], "notes": "Central location"}}
  ],
  "activities": [
    {{"name": "Activity Name", "category": "sightseeing|adventure|food|culture|shopping|entertainment", "estimated_cost_usd": 20.0, "duration": "2-3 hours", "description": "What to expect"}}
  ],
  "day_by_day": [
    {{"day": 1, "date": "{query.departure_date}", "morning": "Detailed morning plan", "afternoon": "Detailed afternoon plan", "evening": "Detailed evening plan", "estimated_daily_cost_usd": 120.0}}
  ],
  "tips": ["Practical tip 1", "Practical tip 2", "Practical tip 3"],
  "total_estimated_cost_usd": 1200.0
}}"""


def _parse_json_response(raw: str) -> Dict:
    """Extract and parse JSON from LLM response, handling markdown fences."""
    # Strip markdown code fences if present
    clean = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.error(f"[Planner] Could not parse JSON from LLM response: {clean[:200]}")
        return _fallback_plan_data()


def _build_response(
    query: TravelQueryRequest,
    data: Dict,
    duration_days: int,
    llm_used: str,
    sources: List[str],
) -> TravelPlanResponse:
    """Convert raw parsed dict into a fully typed TravelPlanResponse."""

    # Parse and deduplicate flights, hotels, and activities
    flights = _deduplicate_flights([FlightResult(**f) for f in data.get("flights", [])])
    hotels  = _deduplicate_hotels([HotelResult(**h)  for h in data.get("hotels",  [])])
    activities = _deduplicate_activities([ActivityResult(**a) for a in data.get("activities", [])])
    
    # FALLBACK: If no activities returned from LLM, generate default ones
    if not activities:
        activities = _generate_default_activities(query.destination, query.trip_type.value)
    
    day_plans  = [DayPlan(**d) for d in data.get("day_by_day", [])]

    return TravelPlanResponse(
        destination=query.destination,
        origin=query.origin,
        duration_days=duration_days,
        travelers=query.travelers,
        total_estimated_cost_usd=float(data.get("total_estimated_cost_usd", 0)),
        budget_usd=query.budget_usd,
        budget_level=query.budget_level.value,
        trip_type=query.trip_type.value,
        summary=data.get("summary", ""),
        highlights=data.get("highlights", []),
        flights=flights,
        hotels=hotels,
        activities=activities,
        day_by_day=day_plans,
        tips=data.get("tips", []),
        llm_used=llm_used,
        search_sources=sources,
    )


def _extract_sources(search_data: Dict[str, str]) -> List[str]:
    """Pull source URLs from formatted search context strings."""
    sources = []
    for block in search_data.values():
        for line in block.split("\n"):
            if line.strip().startswith("Source: http"):
                url = line.replace("Source: ", "").strip()
                if url not in sources:
                    sources.append(url)
    return sources[:10]  # cap at 10 sources


def _fallback_plan_data() -> Dict:
    """Safe empty structure if JSON parsing completely fails."""
    return {
        "summary": "Travel plan could not be generated. Please try again.",
        "highlights": [],
        "flights": [],
        "hotels": [],
        "activities": [],
        "day_by_day": [],
        "tips": ["Please retry your request."],
        "total_estimated_cost_usd": 0.0,
    }


def _deduplicate_hotels(hotels: List[HotelResult]) -> List[HotelResult]:
    """Remove duplicate hotels, keeping only unique ones by name."""
    seen_names = set()
    unique = []
    for hotel in hotels:
        name_lower = hotel.name.lower().strip()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique.append(hotel)
    return unique


def _deduplicate_flights(flights: List[FlightResult]) -> List[FlightResult]:
    """Remove duplicate flights by airline and route."""
    seen = set()
    unique = []
    for flight in flights:
        key = (flight.airline.lower(), flight.route.lower())
        if key not in seen:
            seen.add(key)
            unique.append(flight)
    return unique


def _deduplicate_activities(activities: List[ActivityResult]) -> List[ActivityResult]:
    """Remove duplicate activities by name."""
    seen_names = set()
    unique = []
    for activity in activities:
        name_lower = activity.name.lower().strip()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique.append(activity)
    return unique


def _generate_default_activities(destination: str, trip_type: str) -> List[ActivityResult]:
    """
    Generate sensible default activities if the LLM doesn't return any.
    Ensures the experience selection is never empty.
    """
    defaults = {
        "sightseeing": ActivityResult(
            name=f"City landmarks and monuments tour",
            category="sightseeing",
            estimated_cost_usd=45.0,
            duration="3-4 hours",
            description=f"Explore main attractions and iconic sites in {destination}"
        ),
        "local_cuisine": ActivityResult(
            name="Local cuisine food tour",
            category="food",
            estimated_cost_usd=60.0,
            duration="2-3 hours",
            description=f"Taste authentic dishes and visit popular restaurants in {destination}"
        ),
        "outdoor": ActivityResult(
            name="Outdoor exploration and nature walk",
            category="nature",
            estimated_cost_usd=35.0,
            duration="2-3 hours",
            description=f"Parks, gardens, or outdoor trails near {destination}"
        ),
        "culture": ActivityResult(
            name="Local culture and museums",
            category="culture",
            estimated_cost_usd=25.0,
            duration="2 hours",
            description=f"Museums, galleries, and cultural heritage sites in {destination}"
        ),
        "shopping": ActivityResult(
            name="Shopping and local markets",
            category="shopping",
            estimated_cost_usd=50.0,
            duration="2-3 hours",
            description=f"Explore local bazaars, markets, and shopping districts in {destination}"
        ),
    }
    
    # Return all defaults as a diverse set
    return list(defaults.values())
