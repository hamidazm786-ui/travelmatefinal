from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.models.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(
        full_name=body.full_name.strip(),
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        home_city=body.home_city,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info(f"[Auth] New user registered: {user.email} id={user.id}")

    token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Contact support.")

    await db.execute(update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc)))
    token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserPublic.model_validate(current_user)


@router.patch("/me", response_model=UserPublic)
async def update_profile(
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    await db.execute(update(User).where(User.id == current_user.id).values(**updates))
    await db.refresh(current_user)
    return UserPublic.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    await db.execute(update(User).where(User.id == current_user.id).values(hashed_password=hash_password(body.new_password)))
    return {"message": "Password changed successfully."}


@router.delete("/me")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.delete(current_user)
    return {"message": "Account deleted successfully."}
