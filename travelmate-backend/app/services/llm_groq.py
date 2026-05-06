# app/services/llm_groq.py
# ============================================================
#  Groq LLM Service — Primary AI provider (free tier)
#  Uses groq Python SDK for chat completions.
# ============================================================

from groq import Groq, APIStatusError, APIConnectionError
from app.core.config import get_settings
from app.core.logging import logger
from typing import List, Dict, Optional

settings = get_settings()

# Single client instance reused for all requests
_groq_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    global _groq_client
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


async def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    use_fallback_model: bool = False,
) -> str:
    """
    Send messages to Groq and return the assistant reply text.
    Raises an exception if both Groq models fail (triggers Gemini fallback upstream).
    """
    model = settings.groq_fallback_model if use_fallback_model else settings.groq_model
    client = get_groq_client()

    try:
        logger.info(f"[Groq] Calling model={model} messages={len(messages)}")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        logger.info(f"[Groq] Success — {len(content)} chars returned")
        return content

    except APIStatusError as e:
        if e.status_code == 429 and not use_fallback_model:
            # Rate-limited → retry with secondary Groq model
            logger.warning(f"[Groq] Rate-limited on {model}, retrying with fallback model")
            return await chat_completion(messages, temperature, max_tokens, use_fallback_model=True)
        logger.error(f"[Groq] APIStatusError {e.status_code}: {e.message}")
        raise

    except APIConnectionError as e:
        logger.error(f"[Groq] Connection error: {e}")
        raise


async def generate_travel_plan_prompt(context: Dict) -> str:
    """Build a structured system + user prompt for travel planning."""
    system_prompt = """You are TravelMate, an expert AI travel planner. 
You create detailed, realistic, budget-aware travel itineraries.
Always respond in structured JSON format as instructed.
Be specific with places, costs, and times. Never invent visa requirements."""

    user_prompt = f"""Create a complete travel plan with this information:
- Origin: {context['origin']}
- Destination: {context['destination']}
- Departure: {context['departure_date']}
- Return: {context['return_date']}
- Travelers: {context['travelers']}
- Total Budget: ${context['budget_usd']} USD
- Budget Level: {context['budget_level']}
- Trip Type: {context['trip_type']}
- Extra Notes: {context.get('extra_notes') or 'None'}

Web search data available:
{context.get('search_context', 'No live data — use general knowledge.')}

Respond ONLY with a valid JSON object with these exact keys:
{{
  "summary": "2-3 sentence overview",
  "highlights": ["highlight1", "highlight2", ...],
  "flights": [{{"airline":"...", "route":"...", "estimated_price_usd": 0.0, "duration":"...", "notes":"..."}}],
  "hotels": [{{"name":"...", "location":"...", "price_per_night_usd": 0.0, "rating": 4.5, "amenities":[], "notes":"..."}}],
  "activities": [{{"name":"...", "category":"...", "estimated_cost_usd": 0.0, "duration":"...", "description":"..."}}],
  "day_by_day": [{{"day":1, "date":"YYYY-MM-DD", "morning":"...", "afternoon":"...", "evening":"...", "estimated_daily_cost_usd": 0.0}}],
  "tips": ["tip1", "tip2", ...],
  "total_estimated_cost_usd": 0.0
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]
    return await chat_completion(messages, temperature=0.5, max_tokens=4096)


async def general_chat(
    message: str,
    history: List[Dict[str, str]],
    travel_context: Optional[Dict] = None,
) -> str:
    """General conversational chat with optional travel context injected."""
    system = """You are TravelMate, a friendly and knowledgeable AI travel assistant.
Help users plan trips, answer travel questions, suggest destinations, and give practical advice.
Be concise, warm, and specific."""

    if travel_context:
        system += f"\n\nCurrent trip context: {travel_context['origin']} → {travel_context['destination']}, {travel_context['departure_date']} to {travel_context['return_date']}, budget ${travel_context['budget_usd']}."

    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": message}]
    return await chat_completion(messages, temperature=0.8, max_tokens=1024)


async def analyze_document(text: str, filename: str) -> str:
    """Extract travel-relevant information from uploaded document text."""
    system = "You are a travel document analyst. Extract all travel-related information concisely."
    user = f"""Analyze this document '{filename}' and extract:
1. Any travel destinations mentioned
2. Any dates or durations
3. Any budget or cost information
4. Any travel tips or requirements
5. A brief summary of what this document is about in travel context

Document text:
{text[:6000]}

Respond in JSON:
{{"travel_insights": "...", "detected_destinations": [], "detected_dates": [], "summary": "..."}}"""

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return await chat_completion(messages, temperature=0.3, max_tokens=1024)
