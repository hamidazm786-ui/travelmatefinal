# tests/test_travel_route.py
# ============================================================
#  Basic integration tests for the Travel Plan API
#  Run with: pytest tests/ -v
# ============================================================

from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


# ── Health Check ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "TravelMate AI Backend"


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/health/")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "services" in data


# ── Travel Plan ───────────────────────────────────────────────

MOCK_PLAN = {
    "summary": "A wonderful trip to Istanbul.",
    "highlights": ["Blue Mosque", "Grand Bazaar"],
    "flights": [{"airline": "Turkish Airlines", "route": "LHE → IST", "estimated_price_usd": 450.0, "duration": "7h", "notes": ""}],
    "hotels": [{"name": "Grand Hotel Istanbul", "location": "Sultanahmet", "price_per_night_usd": 80.0, "rating": 4.3, "amenities": ["WiFi"], "notes": ""}],
    "activities": [{"name": "Blue Mosque Visit", "category": "culture", "estimated_cost_usd": 0.0, "duration": "2h", "description": "Iconic mosque"}],
    "day_by_day": [{"day": 1, "date": "2025-06-15", "morning": "Arrive", "afternoon": "Explore", "evening": "Dinner", "estimated_daily_cost_usd": 100.0}],
    "tips": ["Book early", "Carry cash"],
    "total_estimated_cost_usd": 1200.0,
}

SAMPLE_QUERY = {
    "origin": "Lahore, Pakistan",
    "destination": "Istanbul, Turkey",
    "departure_date": "2025-06-15",
    "return_date": "2025-06-22",
    "travelers": 2,
    "budget_usd": 2000.0,
    "budget_level": "moderate",
    "trip_type": "leisure",
}


@pytest.mark.asyncio
async def test_generate_travel_plan():
    with patch("app.services.travel_planner.gather_all_travel_data", new_callable=AsyncMock) as mock_search, \
         patch("app.services.travel_planner.route_llm", new_callable=AsyncMock) as mock_llm:

        mock_search.return_value = {
            "flights": "=== Flights ===\n• Turkish Airlines ~$450",
            "hotels": "=== Hotels ===\n• Grand Hotel $80/night",
            "activities": "=== Activities ===\n• Blue Mosque free",
            "overview": "=== Overview ===\n• Great city",
        }

        import json
        mock_llm.return_value = (json.dumps(MOCK_PLAN), "groq")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/travel/plan", json=SAMPLE_QUERY)
        assert r.status_code == 200

        data = r.json()
        assert data["destination"] == "Istanbul, Turkey"
        assert data["llm_used"] == "groq"
        assert len(data["flights"]) > 0
        assert len(data["day_by_day"]) > 0


# ── Chat ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_message():
    with patch("app.services.chat_service._should_search", return_value=False), \
         patch("app.services.chat_service.route_llm", new_callable=AsyncMock) as mock_llm:

        mock_llm.return_value = ("Istanbul is a beautiful city with rich history!", "groq")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/chat/message", json={"message": "Tell me about Istanbul"})
        assert r.status_code == 200

        data = r.json()
        assert "reply" in data
        assert "session_id" in data
        assert data["llm_used"] == "groq"
