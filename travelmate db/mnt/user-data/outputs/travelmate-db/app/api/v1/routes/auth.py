# app/api/v1/routes/auth.py
# ============================================================
#  /api/v1/auth  — Register, Login, Profile endpoints
# ============================================================

from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.database import get_db
from app.models.models import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    UserPublic, UpdateProfileRequest, ChangePasswordRequest,
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.core.config import get_settings
from app.core.logging import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


# ── POST /api/v1/auth/register ────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.
    Returns a JWT token immediately — user is logged in after registration.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Create user
    user = User(
        full_name=body.full_name.strip(),
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        home_city=body.home_city,
    )
    db.add(user)
    await db.flush()    # get the auto-generated id
    await db.refresh(user)

    logger.info(f"[Auth] New user registered: {user.email} id={user.id}")

    # Issue token
    token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


# ── POST /api/v1/auth/login ───────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Sign in with email + password. Returns a JWT token.
    """
    result = await db.execute(
        select(User).where(User.email == body.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support.",
        )

    # Update last login
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )

    logger.info(f"[Auth] User logged in: {user.email}")

    token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


# ── GET /api/v1/auth/me ───────────────────────────────────────

@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserPublic.model_validate(current_user)


# ── PATCH /api/v1/auth/me ─────────────────────────────────────

@router.patch("/me", response_model=UserPublic)
async def update_profile(
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update profile fields. Only provided fields are changed."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    await db.execute(
        update(User).where(User.id == current_user.id).values(**updates)
    )
    await db.refresh(current_user)

    logger.info(f"[Auth] Profile updated for {current_user.email}")
    return UserPublic.model_validate(current_user)


# ── POST /api/v1/auth/change-password ────────────────────────

@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the authenticated user's password."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(hashed_password=hash_password(body.new_password))
    )
    logger.info(f"[Auth] Password changed for {current_user.email}")
    return {"message": "Password changed successfully."}


# ── DELETE /api/v1/auth/me ────────────────────────────────────

@router.delete("/me")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete the authenticated user's account and all data."""
    await db.delete(current_user)
    logger.info(f"[Auth] Account deleted: {current_user.email}")
    return {"message": "Account deleted successfully."}
