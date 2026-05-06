from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.db.database import get_db
from app.models.models import ChatMessage, ChatSession, User
from app.schemas.plans import ChatMessageOut, ChatSessionDetail, ChatSessionSummary, CreateSessionRequest
from app.schemas.travel import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionSummary, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSession(
        user_id=current_user.id,
        travel_plan_id=body.travel_plan_id,
        travel_context_json=body.travel_context,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return ChatSessionSummary.model_validate(session)


@router.get("/sessions", response_model=List[ChatSessionSummary])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == current_user.id).order_by(desc(ChatSession.updated_at))
    )
    return [ChatSessionSummary.model_validate(session) for session in result.scalars().all()]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    msg_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()
    session_dict = ChatSessionDetail.model_validate(session).model_dump()
    session_dict["messages"] = [ChatMessageOut.model_validate(message) for message in messages]
    return session_dict


@router.post("/sessions/{session_id}/message", response_model=ChatResponse)
async def send_message(
    session_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    request.session_id = session_id
    response = await handle_chat(request)

    user_msg = ChatMessage(session_id=session_id, role="user", content=request.message)
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response.reply,
        llm_used=response.llm_used,
        sources=response.sources,
    )
    db.add(user_msg)
    db.add(ai_msg)
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(
            message_count=ChatSession.message_count + 2,
            title=session.title or request.message[:80],
        )
    )
    logger.info(f"[Chat] Message saved to DB session={session_id} via {response.llm_used}")
    return response


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    await db.delete(session)
