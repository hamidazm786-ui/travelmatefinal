# app/db/database.py
# ============================================================
#  Database engine — async SQLAlchemy + asyncpg
#  Works with ANY PostgreSQL: Neon, Supabase, Railway, local
# ============================================================

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",   # SQL logs in dev only
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,                       # auto-reconnect on disconnect
    pool_recycle=3600,                        # recycle connections every hour
)

# ── Session factory ───────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ── Base class for all ORM models ─────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency — FastAPI route injection ──────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency. Inject with: db: AsyncSession = Depends(get_db)
    Automatically commits on success, rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Create all tables on startup ──────────────────────────────
async def create_tables():
    """Called once at application startup to create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Drop all tables (only for testing) ───────────────────────
async def drop_tables():
    """Only use in tests. Never call in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
