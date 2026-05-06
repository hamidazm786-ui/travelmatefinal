# app/api/v1/routes/chat_db.py
# ============================================================
#  /api/v1/chat  — Chat with full DB persistence
#  Replaces the in-memory _sessions dict with PostgreSQL
# ============================================================

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from typing import List
import uuid

from app.db.database import get_db
from app.models.models import User, ChatSession, ChatMessage
from app.schemas.plans import (
    ChatSessionSummary, ChatSessionDetail,
    ChatMessageOut, CreateSessionRequest,
)
from app.schemas.travel import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat
from app.core.dependencies import get_current_user
from app.core.logging import logger

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── POST /api/v1/chat/sessions  — Create a new session ───────

@router.post("/sessions", response_model=ChatSessionSummary, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session for the authenticated user."""
    session = ChatSession(
        user_id=current_user.id,
        travel_plan_id=body.travel_plan_id,
        travel_context_json=body.travel_context,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    logger.info(f"[Chat] Session created: {session.id} for user {current_user.id}")
    return ChatSessionSummary.model_validate(session)


# ── GET /api/v1/chat/sessions  — List all sessions ───────────

@router.get("/sessions", response_model=List[ChatSessionSummary])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat sessions for the authenticated user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
    )
    sessions = result.scalars().all()
    return [ChatSessionSummary.model_validate(s) for s in sessions]


# ── GET /api/v1/chat/sessions/{session_id}  — Get session ────

@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific chat session with all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    # Load messages
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    session_dict = ChatSessionDetail.model_validate(session).model_dump()
    session_dict["messages"] = [ChatMessageOut.model_validate(m) for m in messages]
    return session_dict


# ── POST /api/v1/chat/sessions/{session_id}/message  ─────────

@router.post("/sessions/{session_id}/message", response_model=ChatResponse)
async def send_message(
    session_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message in a session.
    - Loads history from DB (replaces in-memory store)
    - Calls the LLM via the existing chat_service
    - Saves both user message and AI reply to DB
    """
    # Verify session belongs to user
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    # Load full message history from DB
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    db_messages = msg_result.scalars().all()

    # Build history list for the LLM
    history = [{"role": m.role, "content": m.content} for m in db_messages[-20:]]

    # Override session_id so chat_service uses the DB session id
    request.session_id = session_id

    # Call existing chat service (it handles LLM routing)
    response = await handle_chat(request)

    # Auto-generate title from first user message
    title = session.title
    if not title and session.message_count == 0:
        title = request.message[:80] + ("..." if len(request.message) > 80 else "")

    # Save user message to DB
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)

    # Save assistant reply to DB
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response.reply,
        llm_used=response.llm_used,
        sources=response.sources,
    )
    db.add(ai_msg)

    # Update session metadata
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(
            message_count=ChatSession.message_count + 2,
            title=title,
        )
    )

    logger.info(f"[Chat] Message saved to DB session={session_id} via {response.llm_used}")
    return response


# ── DELETE /api/v1/chat/sessions/{session_id}  ───────────────

@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    await db.delete(session)
    logger.info(f"[Chat] Session deleted: {session_id}")
