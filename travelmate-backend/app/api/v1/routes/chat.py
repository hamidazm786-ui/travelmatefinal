# app/api/v1/routes/chat.py
# ============================================================
#  /api/v1/chat  — Conversational AI endpoints
# ============================================================

from fastapi import APIRouter, HTTPException
from app.schemas.travel import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat, clear_session
from app.core.logging import logger

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse, summary="Send a chat message to TravelMate AI")
async def chat_message(request: ChatRequest):
    """
    Send a message and receive an AI reply.

    - Maintains conversation history per session_id
    - Automatically searches the web for live data when relevant
    - Falls back from Groq to Gemini automatically
    - Optionally accepts a travel_context to ground the conversation
    """
    try:
        return await handle_chat(request)
    except Exception as e:
        logger.error(f"[Route/chat] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}", summary="Clear a conversation session")
async def delete_session(session_id: str):
    """Clear the conversation history for a given session."""
    cleared = clear_session(session_id)
    if cleared:
        return {"message": f"Session '{session_id}' cleared."}
    raise HTTPException(status_code=404, detail="Session not found.")
