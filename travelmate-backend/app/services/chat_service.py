# app/services/chat_service.py
# ============================================================
#  Chat Service — Conversational AI with session memory
#  Handles in-memory conversation history per session_id.
# ============================================================

import uuid
from typing import Dict, List, Optional
from app.schemas.travel import ChatRequest, ChatResponse, ChatMessage
from app.services.llm_router import route_llm
from app.services.search_tavily import search_web
from app.core.logging import logger

# In-memory session store: {session_id: [messages]}
# For production, replace with Redis or a DB.
_sessions: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = """You are TravelMate, a friendly and expert AI travel assistant.
You help users plan trips, discover destinations, find flights and hotels, suggest activities, and give practical travel advice.
You are conversational, warm, and specific. When you don't know current prices, say so honestly.
If the user asks about a specific destination or trip, give detailed and actionable advice."""


async def handle_chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message:
    1. Restore or create session
    2. Optionally search web for current info
    3. Build prompt with history + context
    4. Call LLM via router
    5. Save assistant reply to session
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Restore or initialize session history
    if session_id not in _sessions:
        _sessions[session_id] = []

    session_history = _sessions[session_id]

    # Build travel context string if provided
    travel_ctx_str = ""
    if request.travel_context:
        ctx = request.travel_context
        travel_ctx_str = (
            f"\n\n[Active trip context: {ctx.origin} → {ctx.destination}, "
            f"{ctx.departure_date} to {ctx.return_date}, "
            f"${ctx.budget_usd} budget, {ctx.travelers} traveler(s)]"
        )

    # Detect if we should do a web search to augment the reply
    search_sources: List[str] = []
    search_context = ""
    if _should_search(request.message):
        query = _build_search_query(request.message, request.travel_context)
        results = await search_web(query, max_results=3)
        if results:
            lines = []
            for r in results:
                lines.append(f"• {r.get('title','')}: {r.get('content','')[:300]}")
                url = r.get("url", "")
                if url:
                    search_sources.append(url)
            search_context = "\n\nRelevant live info:\n" + "\n".join(lines)

    # Build system message
    system_content = SYSTEM_PROMPT + travel_ctx_str + search_context

    # Build message list: system + full history + new user message
    messages = [{"role": "system", "content": system_content}]
    messages.extend(session_history[-20:])  # keep last 20 turns
    messages.append({"role": "user", "content": request.message})

    # Call LLM
    reply, llm_used = await route_llm(messages, temperature=0.8, max_tokens=1024)

    # Persist to session
    session_history.append({"role": "user",      "content": request.message})
    session_history.append({"role": "assistant",  "content": reply})
    _sessions[session_id] = session_history

    logger.info(f"[Chat] session={session_id} via {llm_used} history_len={len(session_history)}")

    return ChatResponse(
        reply=reply,
        sources=search_sources,
        llm_used=llm_used,
        session_id=session_id,
    )


def clear_session(session_id: str) -> bool:
    """Clear a session's history."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def _should_search(message: str) -> bool:
    """Determine if the message warrants a live web search."""
    search_triggers = [
        "price", "cost", "cheap", "hotel", "flight", "book",
        "weather", "visa", "current", "now", "today", "latest",
        "best", "recommend", "when to go", "how much",
    ]
    lower = message.lower()
    return any(t in lower for t in search_triggers)


def _build_search_query(message: str, travel_context) -> str:
    """Build a focused search query from the chat message."""
    if travel_context:
        return f"{message} {travel_context.destination} travel"
    return f"{message} travel guide"
