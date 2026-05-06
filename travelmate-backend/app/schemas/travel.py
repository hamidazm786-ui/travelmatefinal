# app/schemas/travel.py
# ============================================================
#  Pydantic v2 schemas — request & response contracts
#  These mirror the frontend's TypeScript interfaces exactly.
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum


# ── Enums ────────────────────────────────────────────────────

class TripType(str, Enum):
    leisure    = "leisure"
    adventure  = "adventure"
    business   = "business"
    family     = "family"
    romantic   = "romantic"


class BudgetLevel(str, Enum):
    budget    = "budget"
    moderate  = "moderate"
    luxury    = "luxury"


# ── Travel Query (frontend → backend) ───────────────────────

class TravelQueryRequest(BaseModel):
    origin: str             = Field(..., json_schema_extra={"example": "Lahore, Pakistan"})
    destination: str        = Field(..., json_schema_extra={"example": "Istanbul, Turkey"})
    departure_date: str     = Field(..., json_schema_extra={"example": "2025-06-15"})
    return_date: str        = Field(..., json_schema_extra={"example": "2025-06-22"})
    travelers: int          = Field(default=1, ge=1, le=20)
    budget_usd: float       = Field(..., gt=0, json_schema_extra={"example": 1500.0})
    budget_level: BudgetLevel = BudgetLevel.moderate
    trip_type: TripType     = TripType.leisure
    extra_notes: Optional[str] = None


# ── Chat (frontend ↔ backend) ────────────────────────────────

class ChatMessage(BaseModel):
    role: str    = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    travel_context: Optional[TravelQueryRequest] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    sources: List[str] = Field(default_factory=list)
    llm_used: str = "groq"
    session_id: Optional[str] = None


# ── Search Results (internal + response) ────────────────────

class FlightResult(BaseModel):
    airline: str
    route: str
    estimated_price_usd: float
    duration: Optional[str] = None
    notes: Optional[str] = None


class HotelResult(BaseModel):
    name: str
    location: str
    price_per_night_usd: float
    rating: Optional[float] = None
    amenities: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ActivityResult(BaseModel):
    name: str
    category: str
    estimated_cost_usd: float
    duration: Optional[str] = None
    description: Optional[str] = None


class SearchResultsResponse(BaseModel):
    destination: str
    flights: List[FlightResult]
    hotels: List[HotelResult]
    activities: List[ActivityResult]
    search_sources: List[str] = Field(default_factory=list)


# ── Full Travel Plan (the main deliverable) ─────────────────

class DayPlan(BaseModel):
    day: int
    date: str
    morning: str
    afternoon: str
    evening: str
    estimated_daily_cost_usd: float


class TravelPlanResponse(BaseModel):
    destination: str
    origin: str
    duration_days: int
    travelers: int
    total_estimated_cost_usd: float
    budget_usd: float
    budget_level: str
    trip_type: str
    summary: str
    highlights: List[str]
    flights: List[FlightResult]
    hotels: List[HotelResult]
    activities: List[ActivityResult]
    day_by_day: List[DayPlan]
    tips: List[str]
    llm_used: str
    search_sources: List[str] = Field(default_factory=list)


# ── File Upload ──────────────────────────────────────────────

class FileAnalysisResponse(BaseModel):
    filename: str
    file_type: str
    extracted_text: str
    travel_insights: str
    detected_destinations: List[str] = Field(default_factory=list)
    detected_dates: List[str] = Field(default_factory=list)
    llm_used: str


# ── Health Check ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]
