# app/schemas/plans.py
# ============================================================
#  Travel plan + chat Pydantic schemas for DB-backed endpoints
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Travel plan list item (for /plans endpoint) ────────────────

class TravelPlanSummary(BaseModel):
    id: str
    origin: str
    destination: str
    departure_date: str
    return_date: str
    duration_days: int
    travelers: int
    budget_usd: float
    budget_level: str
    trip_type: str
    summary: Optional[str]
    total_estimated_cost_usd: Optional[float]
    status: str
    is_favourite: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Full travel plan (single plan detail) ─────────────────────

class TravelPlanDetail(TravelPlanSummary):
    plan_json: dict     # full generated itinerary
    llm_used: Optional[str]
    extra_notes: Optional[str]
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Save plan request ─────────────────────────────────────────

class SavePlanRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: str
    duration_days: int
    travelers: int
    budget_usd: float
    budget_level: str
    trip_type: str
    extra_notes: Optional[str] = None
    plan_json: dict
    summary: Optional[str] = None
    total_estimated_cost_usd: Optional[float] = None
    llm_used: Optional[str] = None


# ── Update plan ────────────────────────────────────────────────

class UpdatePlanRequest(BaseModel):
    status: Optional[str]       = None
    is_favourite: Optional[bool] = None
    extra_notes: Optional[str]  = None


# ── Chat session ──────────────────────────────────────────────

class ChatSessionSummary(BaseModel):
    id: str
    title: Optional[str]
    message_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Chat message ──────────────────────────────────────────────

class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    llm_used: Optional[str]
    sources: Optional[List[str]]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat session with messages ────────────────────────────────

class ChatSessionDetail(ChatSessionSummary):
    messages: List[ChatMessageOut] = []

    model_config = {"from_attributes": True}


# ── Create session ────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    travel_plan_id: Optional[str] = None
    travel_context: Optional[dict] = None


# ── User stats (for dashboard) ────────────────────────────────

class UserStats(BaseModel):
    total_trips: int
    total_spent_usd: float
    favourite_destination: Optional[str]
    most_used_llm: Optional[str]
    trips_this_month: int
