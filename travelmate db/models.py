# app/models/models.py
# ============================================================
#  SQLAlchemy ORM Models — maps Python classes to DB tables
#  Tables: users, travel_plans, chat_sessions, chat_messages
# ============================================================

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Float, Integer, Boolean,
    DateTime, ForeignKey, JSON, Enum as SAEnum,
    func, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ── helpers ───────────────────────────────────────────────────

def _uuid() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.utcnow()


# ════════════════════════════════════════════════════════════
#  TABLE 1: users
#  Stores registered accounts, hashed passwords, profile data
# ════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Profile preferences (no hardcoding — stored per user in DB)
    preferred_style: Mapped[str] = mapped_column(
        String(20), default="moderate"   # budget | moderate | luxury
    )
    preferred_trip_type: Mapped[str] = mapped_column(
        String(20), default="leisure"    # leisure | adventure | business | family | romantic
    )
    home_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Account metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    travel_plans:   Mapped[list["TravelPlan"]]   = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_sessions:  Mapped[list["ChatSession"]]  = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


# ════════════════════════════════════════════════════════════
#  TABLE 2: travel_plans
#  Each generated itinerary is saved here as JSON + metadata
# ════════════════════════════════════════════════════════════

class TravelPlan(Base):
    __tablename__ = "travel_plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Trip basics — no hardcoding, all stored from user input
    origin: Mapped[str]       = mapped_column(String(200), nullable=False)
    destination: Mapped[str]  = mapped_column(String(200), nullable=False)
    departure_date: Mapped[str] = mapped_column(String(20), nullable=False)
    return_date: Mapped[str]    = mapped_column(String(20), nullable=False)
    duration_days: Mapped[int]  = mapped_column(Integer, nullable=False)
    travelers: Mapped[int]      = mapped_column(Integer, default=1)
    budget_usd: Mapped[float]   = mapped_column(Float, nullable=False)
    budget_level: Mapped[str]   = mapped_column(String(20), default="moderate")
    trip_type: Mapped[str]      = mapped_column(String(20), default="leisure")
    extra_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Generated output — full plan stored as JSON
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Summary fields (indexed for quick list views)
    summary: Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    total_estimated_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_used: Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="completed"  # planning | completed | archived
    )
    is_favourite: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="travel_plans")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_travel_plans_user_created", "user_id", "created_at"),
        Index("ix_travel_plans_destination",  "destination"),
    )

    def __repr__(self) -> str:
        return f"<TravelPlan id={self.id} {self.origin}→{self.destination}>"


# ════════════════════════════════════════════════════════════
#  TABLE 3: chat_sessions
#  One session = one conversation thread per user
# ════════════════════════════════════════════════════════════

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Optional link to a travel plan (when chatting about a specific trip)
    travel_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("travel_plans.id", ondelete="SET NULL"),
        nullable=True
    )

    # Session metadata
    title: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True    # auto-generated from first message
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool]    = mapped_column(Boolean, default=True)

    # Optional travel context snapshot
    travel_context_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user:     Mapped["User"]          = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} user={self.user_id}>"


# ════════════════════════════════════════════════════════════
#  TABLE 4: chat_messages
#  Every message in a conversation — both user and AI
# ════════════════════════════════════════════════════════════

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Message content
    role: Mapped[str]    = mapped_column(String(20), nullable=False)   # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI metadata (only on assistant messages)
    llm_used: Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    sources:  Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # web search URLs

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role={self.role}>"
